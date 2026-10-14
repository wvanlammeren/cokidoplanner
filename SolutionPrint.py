from ortools.sat.python import cp_model
import numpy as np


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """
    Solution processing
    Check on every solution the total value, if it is higher keep it.
    Keep top 5 solutions in a dict and every time a bettter one is found push the last one out
    """

    def __init__(self, resultstokeep, shifts, num_parents, num_days, limit, costmatrix):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._shifts = shifts
        self._num_parents = num_parents
        self._num_days = num_days
        self._solution_count = 0
        self._solution_limit = limit
        self._costmatrix = costmatrix
        self._maxcost = 0
        self._optimal = []
        self._val_list = [0] * resultstokeep
        self._sol_list = [0] * resultstokeep
        print('SolutionPrinter initiated')

    def on_solution_callback(self):
        cost = 0
        sol = np.zeros((self._num_parents, self._num_days))
        self._solution_count += 1
        # print('----Matrix Solution %i----' % self._solution_count)

        if (self._solution_count + 1) % 1000 == 0:
            print(self._solution_count)
        # calculate cost

        for j in range(self._num_days):
            for i in range(self._num_parents):
                if self.Value(self._shifts[(i, j)]):
                    sol[i, j] = 1
                    cost += self._costmatrix[i][j]

        if cost >= self._maxcost:
            self._maxcost = cost
            self._optimal = sol
            self._val_list = [cost] + self._val_list
            self._val_list.pop(-1)
            self._sol_list = [sol] + self._sol_list
            self._sol_list.pop(-1)

        if self._solution_count >= self._solution_limit:
            print('Stop search after %i solutions' % self._solution_limit)
            print('---------------------')
            print('Optimal solution Cost :', self._maxcost)
            print(np.matrix(self._optimal))
            self.StopSearch()

    def solution_count(self):
        return self._solution_count

    def optimal_solution(self):
        print('called optimal_solution')
        print(np.matrix(self._optimal))
        print("Cost=", self._maxcost)

    def top_results(self):
        return {"optimization_value": self._val_list, "solutions": self._sol_list}
