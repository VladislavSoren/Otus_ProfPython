from scipy import sparse
import numpy as np


class LogisticRegression():

    def __init__(self):
        self.w = None
        self.loss_history = []

    def train(self, x, y, num_iters=1, learning_rate=1e-1, batch_size=200, reg=1e-5, verbose=False):

        num_train, dim = x.shape

        # инициализирует веса
        if self.w is None:
            self.w = np.random.randn(dim) * 0.01

        # добавит столбец из единиц
        self.append_biases(x)

        loss_history = []

        for it in range(num_iters):
            # print(it)
            for batch_start in range(0, x.shape[0], batch_size):
                random_indices = np.random.choice(num_train, batch_size)
                X_batch = x[random_indices]
                y_batch = y[random_indices]

                # метод сделает прогноз с текущими весами
                y_pred = self.h(X_batch, self.w)

                # найдет и запишет уровень ошибки
                loss = self.objective(y_batch, y_pred)
                regularization_loss = (reg / (2 * dim)) * np.sum(np.square(self.w[1:]))
                loss += regularization_loss
                loss_history.append(loss)

                # рассчитает градиент
                grad = self.gradient(X_batch, y_batch, y_pred, dim)
                regularization_grad = (reg / dim) * self.w
                regularization_grad[0] = 0
                grad += regularization_grad

                # и обновит веса
                self.w -= learning_rate * grad

            if verbose and it % 100 == 0:
                print('iteration %d / %d: loss %f' % (it, num_iters, loss))

        self.loss_history = loss_history

    # метод .predict() делает прогноз с помощью обученной модели
    def predict(self, x):
        self.append_biases(x)

        z = np.dot(x.toarray(), self.w)
        probs = np.array([self.stable_sigmoid(value) for value in z])

        return np.where(probs >= 0.5, 1, 0)
        # return np.where(probs >= 0.5, 1, 0), probs

    def append_biases(self, X):
        return sparse.hstack((np.ones(X.shape[0])[:, np.newaxis], X)).tocsr()

    def h(self, x, w):
        z = np.dot(x.toarray(), w)
        return np.array([self.stable_sigmoid(value) for value in z])

    def objective(self, y, y_pred):
        y_one_loss = y * np.log(y_pred + 1e-9)
        y_zero_loss = (1 - y) * np.log(1 - y_pred + 1e-9)
        return -np.mean(y_zero_loss + y_one_loss)

    def gradient(self, x, y, y_pred, dim):
        return np.dot(x.toarray().T, (y_pred - y)) / dim

    def stable_sigmoid(self, z):
        if z >= 0:
            return 1 / (1 + np.exp(-z))
        else:
            return np.exp(z) / (np.exp(z) + 1)
