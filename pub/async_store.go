package main

import (
	"net/http"
	"sync"
	"time"

	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

type AsyncTaskStore struct {
	localTasks        map[string]*AsyncTask
	jobHttpClient     *http.Client
	replicaHttpClient *http.Client
	rwMutex           sync.RWMutex
	longPollTimeout   time.Duration
	replicaDiscovery  *replicaDiscovery
	cleanUpTimeout    time.Duration
	taskStorage       TaskStorage
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
	attempts         int
	pubInstanceAddr  string
	doneChannel      chan string // channel to notify when task is done
}

type TaskStatus string

const (
	Ongoing   TaskStatus = "ongoing"
	Completed TaskStatus = "completed"
	Failed    TaskStatus = "failed"
)

func NewAsyncTaskStore(replicaDiscovery *replicaDiscovery, taskStorage TaskStorage) *AsyncTaskStore {
	store := &AsyncTaskStore{
		localTasks: make(map[string]*AsyncTask),
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
		taskStorage:      taskStorage,
	}
	go store.cleanUpRoutine()
	return store
}

func (s *AsyncTaskStore) CreateTask(task *AsyncTask) *AsyncTask {
	s.rwMutex.Lock()
	s.localTasks[task.id] = task
	s.taskStorage.Create(task)
	s.rwMutex.Unlock()
	return task
}

func (s *AsyncTaskStore) UpdateTask(task *AsyncTask) *AsyncTask {
	s.rwMutex.Lock()
	s.localTasks[task.id] = task
	s.taskStorage.Update(task)
	s.rwMutex.Unlock()
	return task
}

func (s *AsyncTaskStore) GetTask(taskId string) (*AsyncTask, bool) {
	s.rwMutex.RLock()
	task, ok := s.localTasks[taskId]
	s.rwMutex.RUnlock()
	return task, ok
}

func (s *AsyncTaskStore) DeleteTask(taskId string) {
	s.rwMutex.Lock()
	delete(s.localTasks, taskId)
	s.taskStorage.Delete(taskId)
	s.rwMutex.Unlock()
}

func (s *AsyncTaskStore) cleanUpRoutine() {
	for {
		time.Sleep(5 * time.Minute)
		s.rwMutex.Lock()
		for taskId, task := range s.localTasks {
			if task.startedAt.Add(s.cleanUpTimeout).Before(time.Now()) {
				log.Info("Cleaning up obsolete async call task", log.Ctx{
					"taskId":     task.id,
					"started_at": task.startedAt,
				})
				delete(s.localTasks, taskId)
			}
		}
		s.rwMutex.Unlock()
	}
}

// Persistent storage for async tasks
type TaskStorage interface {
	Create(task *AsyncTask) error
	Read(taskId string) (*AsyncTask, error)
	Update(task *AsyncTask) error
	Delete(taskId string) error
}

type lifecycleTaskStorage struct {
}

func NewLifecycleTaskStorage() *lifecycleTaskStorage {
	return &lifecycleTaskStorage{}
}

type memoryTaskStorage struct {
	tasks map[string]*AsyncTask
}

func NewMemoryTaskStorage() TaskStorage {
	return &memoryTaskStorage{
		tasks: make(map[string]*AsyncTask),
	}
}

func (s *memoryTaskStorage) Read(taskId string) (*AsyncTask, error) {
	task, ok := s.tasks[taskId]
	if !ok {
		return nil, errors.New("Task not found")
	}
	return task, nil
}

func (s *memoryTaskStorage) Create(task *AsyncTask) error {
	s.tasks[task.id] = task
	return nil
}

func (s *memoryTaskStorage) Update(task *AsyncTask) error {
	s.tasks[task.id] = task
	return nil
}

func (s *memoryTaskStorage) Delete(taskId string) error {
	delete(s.tasks, taskId)
	return nil
}
