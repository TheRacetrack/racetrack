import logging
import pickle

from sklearn.datasets import make_regression
from sklearn.linear_model import LinearRegression

if __name__ == '__main__':
    x_train, y_train = make_regression(n_samples=100, n_features=2, noise=0.1)
    model = LinearRegression()
    model.fit(x_train, y_train)

    with open('model.pickle', 'wb') as f:
        pickle.dump(model, f)

    logging.getLogger(__name__).info('model pickled')
