package main

type Services struct {
	config         *Config
	asyncTaskStore *AsyncTaskStore
	lifecycleCache *LifecycleCache
}

func InitServices(cfg *Config) *Services {
	replicaDiscovery := NewReplicaDiscovery(cfg)
	taskStorage := NewLifecycleTaskStorage(cfg.LifecycleUrl, cfg.LifecycleToken)
	asyncTaskStore := NewAsyncTaskStore(replicaDiscovery, taskStorage)

	lifecycleCache := NewLifecycleCache(cfg)

	return &Services{
		config:         cfg,
		asyncTaskStore: asyncTaskStore,
		lifecycleCache: lifecycleCache,
	}
}

func (s *Services) Shutdown() {
	s.asyncTaskStore.CancelOngoingRequests()
}
