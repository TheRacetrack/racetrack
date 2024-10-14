package main

import (
	"crypto/sha256"
	"sync"
	"time"
)

type LifecycleCache struct {
	cachedResponses map[AuthorizeCallRequest]*AuthorizeCallResponse
	rwMutex         sync.RWMutex
	timeToLive      time.Duration
	cleanUpPeriod   time.Duration
}

type AuthorizeCallRequest struct {
	JobName       string
	JobVersion    string
	Endpoint      string
	AuthTokenHash string
}

type AuthorizeCallResponse struct {
	AuthData  *JobCallAuthData
	createdAt time.Time
}

func NewLifecycleCache(cfg *Config) *LifecycleCache {
	cache := &LifecycleCache{
		cachedResponses: make(map[AuthorizeCallRequest]*AuthorizeCallResponse),
		timeToLive:      time.Duration(cfg.LifecycleCacheTTL) * time.Second,
		cleanUpPeriod:   1 * time.Minute,
	}
	go cache.cleanUpRoutine()
	return cache
}

func (c *LifecycleCache) Put(jobName, jobVersion, endpoint, authToken string, authData *JobCallAuthData) {
	request := AuthorizeCallRequest{
		JobName:       jobName,
		JobVersion:    jobVersion,
		Endpoint:      endpoint,
		AuthTokenHash: calculateHash(authToken),
	}
	response := &AuthorizeCallResponse{
		AuthData:  authData,
		createdAt: time.Now(),
	}
	c.rwMutex.Lock()
	c.cachedResponses[request] = response
	c.rwMutex.Unlock()
}

func (c *LifecycleCache) Get(jobName, jobVersion, endpoint, authToken string) (*AuthorizeCallResponse, bool) {
	request := AuthorizeCallRequest{
		JobName:       jobName,
		JobVersion:    jobVersion,
		Endpoint:      endpoint,
		AuthTokenHash: calculateHash(authToken),
	}
	c.rwMutex.RLock()
	defer c.rwMutex.RUnlock()
	task, ok := c.cachedResponses[request]
	return task, ok
}

func (c *LifecycleCache) cleanUpRoutine() {
	for {
		time.Sleep(c.cleanUpPeriod)
		c.rwMutex.Lock()
		for request, response := range c.cachedResponses {
			if response.createdAt.Add(c.timeToLive).Before(time.Now()) {
				delete(c.cachedResponses, request)
			}
		}
		c.rwMutex.Unlock()
	}
}

func calculateHash(input string) string {
	hasher := sha256.New()
	hasher.Write([]byte(input))
	return string(hasher.Sum(nil))
}
