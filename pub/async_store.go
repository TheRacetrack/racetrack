package main

import (
	"bytes"
	"encoding/json"
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
	Id                 string      `json:"id"`
	Status             TaskStatus  `json:"status"`
	StartedAtTimestamp int64       `json:"started_at"`
	EndedAtTimestamp   *int64      `json:"ended_at"`
	ErrorMessage       *string     `json:"error"`
	JobName            string      `json:"job_name"`
	JobVersion         string      `json:"job_version"`
	JobPath            string      `json:"job_path"`
	Url                string      `json:"url"`
	HttpMethod         string      `json:"method"`
	RequestData        []byte      `json:"request_data"`
	ResponseData       []byte      `json:"response_data"`
	ResponseJson       interface{} `json:"response_json"`
	ResponseStatusCode *int        `json:"response_status_code"`
	Attempts           int         `json:"attempts"`
	PubInstanceAddr    string      `json:"pub_instance"`
	startedAt          time.Time
	endedAt            *time.Time
	resultHeaders      map[string]string
	doneChannel        chan string // channel to notify when task is done
}

type TaskStatus string

const (
	Ongoing   TaskStatus = "ongoing"
	Completed TaskStatus = "completed"
	Failed    TaskStatus = "failed"
)

var ErrAsyncTaskNotFound = errors.New("Async task not found")

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
	s.localTasks[task.Id] = task
	s.taskStorage.Create(task)
	s.rwMutex.Unlock()
	return task
}

func (s *AsyncTaskStore) UpdateTask(task *AsyncTask) *AsyncTask {
	s.rwMutex.Lock()
	s.localTasks[task.Id] = task
	s.taskStorage.Update(task)
	s.rwMutex.Unlock()
	return task
}

func (s *AsyncTaskStore) GetLocalTask(taskId string) (*AsyncTask, bool) {
	s.rwMutex.RLock()
	task, ok := s.localTasks[taskId]
	s.rwMutex.RUnlock()
	return task, ok
}

func (s *AsyncTaskStore) GetStoredTask(taskId string) (*AsyncTask, error) {
	task, err := s.taskStorage.Read(taskId)
	return task, err
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
					"taskId":     task.Id,
					"started_at": task.startedAt,
				})
				delete(s.localTasks, taskId)
			}
		}
		s.rwMutex.Unlock()
	}
}

// Persistent storage keeping all async tasks in one place
type TaskStorage interface {
	Create(task *AsyncTask) error
	Read(taskId string) (*AsyncTask, error)
	Update(task *AsyncTask) error
	Delete(taskId string) error
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
		return nil, ErrAsyncTaskNotFound
	}
	return task, nil
}

func (s *memoryTaskStorage) Create(task *AsyncTask) error {
	s.tasks[task.Id] = task
	return nil
}

func (s *memoryTaskStorage) Update(task *AsyncTask) error {
	s.tasks[task.Id] = task
	return nil
}

func (s *memoryTaskStorage) Delete(taskId string) error {
	delete(s.tasks, taskId)
	return nil
}

type lifecycleTaskStorage struct {
	lcClient *lifecycleClient
}

func NewLifecycleTaskStorage(
	lifecycleUrl string,
	internalToken string,
) TaskStorage {
	return &lifecycleTaskStorage{
		lcClient: &lifecycleClient{
			lifecycleUrl:  lifecycleUrl,
			internalToken: internalToken,
			httpClient: &http.Client{
				Timeout:   10 * time.Second,
				Transport: defaultLifecycleTransport,
			},
		},
	}
}

func (s *lifecycleTaskStorage) Read(taskId string) (*AsyncTask, error) {
	url := JoinURL(s.lcClient.lifecycleUrl, "/api/v1/job/async/call/", taskId)
	task := &AsyncTask{}
	err := s.lcClient.getRequest(url, true, "getting async task", true, task)
	if err != nil {
		return nil, err
	}
	return task, nil
}

func (s *lifecycleTaskStorage) Create(task *AsyncTask) error {
	url := JoinURL(s.lcClient.lifecycleUrl, "/api/v1/job/async/call")
	bodyBytes, err := json.Marshal(task)
	if err != nil {
		return errors.Wrap(err, "marshalling async task to JSON")
	}
	return s.lcClient.makeRequest("POST", url, true, "creating async task", false, nil, bytes.NewBuffer(bodyBytes))
}

func (s *lifecycleTaskStorage) Update(task *AsyncTask) error {
	url := JoinURL(s.lcClient.lifecycleUrl, "/api/v1/job/async/call/", task.Id)
	bodyBytes, err := json.Marshal(task)
	if err != nil {
		return errors.Wrap(err, "marshalling async task to JSON")
	}
	return s.lcClient.makeRequest("PUT", url, true, "updating async task", false, nil, bytes.NewBuffer(bodyBytes))
}

func (s *lifecycleTaskStorage) Delete(taskId string) error {
	url := JoinURL(s.lcClient.lifecycleUrl, "/api/v1/job/async/call/", taskId)
	return s.lcClient.makeRequest("DELETE", url, true, "deleting async task", false, nil, nil)
}
