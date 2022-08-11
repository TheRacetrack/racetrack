from typing import Dict, Callable


class AuxiliaryEntrypoints:
    def perform(self, x: float, y: float) -> float:
        """
        Add numbers.
        :param x: First element to add.
        :param y: Second element to add.
        :return: Sum of the numbers.
        """
        return x + y

    def auxiliary_endpoints(self) -> Dict[str, Callable]:
        return {
            '/explain': self.explain,
            '/random': self.random,
        }

    def explain(self, x: float, y: float) -> Dict[str, float]:
        """
        Explain feature importance of a model result.
        :param x: First element to add.
        :param y: Second element to add.
        :return: Dict of feature importance.
        """
        result = self.perform(x, y)
        return {'x_importance': x / result, 'y_importance': y / result}

    def random(self) -> float:
        """Return random number"""
        return 4  # chosen by fair dice roll

    def docs_input_examples(self) -> Dict[str, Dict]:
        return {
            '/perform': {
                'x': 40,
                'y': 2,
            },
            '/explain': {
                'x': 1,
                'y': 2,
            },
            '/random': {},
        }
