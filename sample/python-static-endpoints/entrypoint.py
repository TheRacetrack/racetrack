class JobEntrypoint:
    def perform(self, x: float, y: float) -> float:
        """
        Add numbers.
        :param x: First element to add.
        :param y: Second element to add.
        :return: Sum of the numbers.
        """
        return x + y

    def static_endpoints(self):
        """Dict of endpoint paths mapped to corresponding static files that ought be served."""
        return {
            '/xrai': 'xrai.yaml',
            '/manifest': ('job.yaml', 'application/x-yaml'),
            '/docs/readme': 'README.md',
        }
