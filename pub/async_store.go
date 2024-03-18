package main

import (
	"encoding/json"
	"net/http"
	"sync"
	"time"

	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

var defaultAsyncJobTransport http.RoundTripper = defaultHttpTransport()
var defaultAsyncReplicaTransport http.RoundTripper = defaultHttpTransport()

type AsyncTaskStore struct {
	localTasks            map[string]*AsyncTask
	jobHttpClient         *http.Client // HTTP client to make requests to jobs
	replicaPollHttpClient *http.Client // HTTP client to poll result from other replica
	replicaHttpClient     *http.Client // HTTP client to check task status in other replica
	rwMutex               sync.RWMutex
	longPollTimeout       time.Duration
	replicaDiscovery      *replicaDiscovery
	cleanUpTimeout        time.Duration
	taskStorage           TaskStorage
}

type AsyncTask struct {
	Id                 string            `json:"id"`
	Status             TaskStatus        `json:"status"`
	StartedAtTimestamp int64             `json:"started_at"`
	EndedAtTimestamp   *int64            `json:"ended_at"`
	ErrorMessage       *string           `json:"error"`
	JobName            string            `json:"job_name"`
	JobVersion         string            `json:"job_version"`
	JobPath            string            `json:"job_path"`
	RequestMethod      string            `json:"request_method"`
	RequestUrl         string            `json:"request_url"`
	RequestHeaders     map[string]string `json:"request_headers"`
	RequestBody        string            `json:"request_body"`
	ResponseStatusCode *int              `json:"response_status_code"`
	ResponseHeaders    map[string]string `json:"response_headers"`
	ResponseBody       string            `json:"response_body"`
	Attempts           int               `json:"attempts"`
	PubInstanceAddr    string            `json:"pub_instance_addr"`
	startedAt          time.Time
	endedAt            *time.Time
	doneChannel        chan string // channel to notify when task is done
}

type AsyncTaskStatusDto struct {
	Id     string     `json:"task_id"`
	Status TaskStatus `json:"status"`
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
		replicaPollHttpClient: &http.Client{
			Timeout:   120 * time.Minute,
			Transport: defaultAsyncReplicaTransport,
		},
		replicaHttpClient: &http.Client{
			Timeout:   5 * time.Second,
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

func (s *AsyncTaskStore) CreateTask(task *AsyncTask) (*AsyncTask, error) {
	s.rwMutex.Lock()
	defer s.rwMutex.Unlock()
	s.localTasks[task.Id] = task
	err := s.taskStorage.Create(task)
	if err != nil {
		return nil, err
	}
	return task, nil
}

func (s *AsyncTaskStore) UpdateTask(task *AsyncTask) error {
	s.rwMutex.Lock()
	defer s.rwMutex.Unlock()
	s.localTasks[task.Id] = task
	err := s.taskStorage.Update(task)
	return err
}

func (s *AsyncTaskStore) GetLocalTask(taskId string) (*AsyncTask, bool) {
	s.rwMutex.RLock()
	defer s.rwMutex.RUnlock()
	task, ok := s.localTasks[taskId]
	return task, ok
}

func (s *AsyncTaskStore) GetStoredTask(taskId string) (*AsyncTask, error) {
	task, err := s.taskStorage.Read(taskId)
	return task, err
}

func (s *AsyncTaskStore) DeleteTask(taskId string) error {
	s.rwMutex.Lock()
	defer s.rwMutex.Unlock()
	delete(s.localTasks, taskId)
	err := s.taskStorage.Delete(taskId)
	return err
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

				go func(taskId string) {
					err := s.DeleteTask(task.Id)
					if err != nil {
						log.Error("Failed to delete obsolete async task", log.Ctx{
							"taskId": task.Id,
							"error":  err.Error(),
						})
						return
					}
					log.Info("Obsolete task has been deleted", log.Ctx{
						"taskId": task.Id,
						"status": task.Status,
					})
				}(taskId)
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
	err := s.lcClient.makeRequest("GET", url, true, "getting async task", nil, true, task)
	if err != nil {
		if errors.As(err, &NotFoundError{}) {
			return nil, ErrAsyncTaskNotFound
		}
		return nil, err
	}
	return task, nil
}

func (s *lifecycleTaskStorage) Create(task *AsyncTask) error {
	url := JoinURL(s.lcClient.lifecycleUrl, "/api/v1/job/async/call")
	jsonBody, err := json.Marshal(task)
	if err != nil {
		return errors.Wrap(err, "marshalling async task to JSON")
	}
	return s.lcClient.makeRequest("POST", url, true, "creating async task", jsonBody, false, nil)
}

func (s *lifecycleTaskStorage) Update(task *AsyncTask) error {
	url := JoinURL(s.lcClient.lifecycleUrl, "/api/v1/job/async/call/", task.Id)
	jsonBody, err := json.Marshal(task)
	if err != nil {
		return errors.Wrap(err, "marshalling async task to JSON")
	}
	return s.lcClient.makeRequest("PUT", url, true, "updating async task", jsonBody, false, nil)
}

func (s *lifecycleTaskStorage) Delete(taskId string) error {
	url := JoinURL(s.lcClient.lifecycleUrl, "/api/v1/job/async/call/", taskId)
	return s.lcClient.makeRequest("DELETE", url, true, "deleting async task", nil, false, nil)
}
