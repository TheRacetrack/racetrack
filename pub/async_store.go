package main

import (
	"net/http"
	"sync"
	"time"

	log "github.com/inconshreveable/log15"
)

type AsyncTaskStore struct {
	tasks             map[string]*AsyncTask
	jobHttpClient     *http.Client
	replicaHttpClient *http.Client
	rwMutex           sync.RWMutex
	longPollTimeout   time.Duration
	replicaDiscovery  *replicaDiscovery
	cleanUpTimeout    time.Duration
}

type AsyncTask struct {
	id               string
	status           TaskStatus
	jobName          string
	jobVersion       string
	jobPath          string
	httpMethod       string
	startedAt        time.Time
	endedAt          *time.Time
	resultData       []byte
	resultHeaders    map[string]string
	resultStatusCode *int
	result           interface{}
	errorMessage     *string
	doneChannel      chan string // channel to notify when task is done
}

type TaskStatus string

const (
	Ongoing   TaskStatus = "ongoing"
	Completed TaskStatus = "completed"
	Failed    TaskStatus = "failed"
)

func NewAsyncTaskStore(replicaDiscovery *replicaDiscovery) *AsyncTaskStore {
	store := &AsyncTaskStore{
		tasks: make(map[string]*AsyncTask),
		jobHttpClient: &http.Client{
			Timeout:   120 * time.Minute,
			Transport: defaultAsyncJobTransport,
		},
		replicaHttpClient: &http.Client{
			Timeout:   120 * time.Minute,
			Transport: defaultAsyncReplicaTransport,
		},
		longPollTimeout:  30 * time.Second,
		cleanUpTimeout:   125 * time.Minute,
		replicaDiscovery: replicaDiscovery,
	}
	go store.cleanUpRoutine()
	return store
}

func (s *AsyncTaskStore) SaveTask(task *AsyncTask) *AsyncTask {
	s.rwMutex.Lock()
	s.tasks[task.id] = task
	s.rwMutex.Unlock()
	return task
}

func (s *AsyncTaskStore) GetTask(taskId string) (*AsyncTask, bool) {
	s.rwMutex.RLock()
	task, ok := s.tasks[taskId]
	s.rwMutex.RUnlock()
	return task, ok
}

func (s *AsyncTaskStore) DeleteTask(taskId string) {
	s.rwMutex.Lock()
	delete(s.tasks, taskId)
	s.rwMutex.Unlock()
}

func (s *AsyncTaskStore) cleanUpRoutine() {
	for {
		time.Sleep(5 * time.Minute)
		s.rwMutex.Lock()
		for taskId, task := range s.tasks {
			if task.startedAt.Add(s.cleanUpTimeout).Before(time.Now()) {
				log.Info("Cleaning up obsolete async call task", log.Ctx{
					"taskId":     task.id,
					"started_at": task.startedAt,
				})
				delete(s.tasks, taskId)
			}
		}
		s.rwMutex.Unlock()
	}
}
