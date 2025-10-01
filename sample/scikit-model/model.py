import logging
import pickle
from typing import List


class ScikitDummyModel:
    def __init__(self):
        with open('model.pickle', 'rb') as fh:
            self.model = pickle.load(fh)
        logging.getLogger(__name__).info('model unpickled')

    def perform(self, x_new: List[float]) -> List[float]:
        """
        Perform single prediction on new data.
        :param x_new: new data point (list of two coordinates)
        :return: predicted values
        """
        ynew = self.model.predict([x_new])
        return ynew.tolist()

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'x_new': [10, 20],
        }
