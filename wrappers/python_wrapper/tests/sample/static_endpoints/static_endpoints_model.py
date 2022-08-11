class StaticEndpoints:
    def perform(self):
        pass

    def static_endpoints(self):
        return {
            '/xrai': ('sample/static_endpoints/xrai.yaml', 'application/x-yaml'),
            '/docs': './sample/static_endpoints/docs',
        }
