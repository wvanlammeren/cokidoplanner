from ortools.sat.python import cp_model
import pandas as pd
from GsheetWrapper import GsheetWrapper
from DataHandler import CokidoDataHandler
from SolutionPrint import SolutionPrinter
import math


def run_calculation():
    print('starting')
    # creategsheet document and process data data
    doc = GsheetWrapper()
    sheet = doc.get_document()
    data = CokidoDataHandler(sheet)
    data.import_data()
    data.update_gsheet()

    # create model
    all_parents = range(0, data.num_parents, 1)
    all_families = range(0, data.num_families, 1)
    all_days = range(0, data.num_days, 1)
    model = cp_model.CpModel()

    # Create the boolean model variables shift(i,j) with i=parentID j=day in the model (1=present, 0=not present)
    shifts = {}
    for i in all_parents:
        for j in all_days:
            shifts[(i, j)] = model.NewBoolVar('shift_p%i_d%i' % (i, j))

    print('adding constraints')
    # Contraint 1 : set number of parents for every day:
    # -- On day j ,sum of all the variables shift(i,j) = req_presence[j] : we need sum parents on day j
    for j in all_days:
        model.Add(sum(shifts[i, j] for i in all_parents) == data.np_req_presence[j])

    # Constraint 2 : set max number of days per family -->
    _parent_tracker = 0
    # tracks where we are going down the matrix of parents per family.
    # we need to do it this way because matrix multiplication doesn't work in ortools
    for famid in all_families:

        if data.df_fam.parents.values[famid] == 1:
            model.Add(sum(shifts[_parent_tracker, j] for j in all_days) <= data.np_presence_req_per_fam[famid])
            _parent_tracker = _parent_tracker + 1
            print('added 1 parent')

        elif data.df_fam.parents.values[famid] == 2:
            model.Add(sum(shifts[_parent_tracker, j] + shifts[_parent_tracker + 1, j] for j in all_days) <=
                      data.np_presence_req_per_fam[famid])
            _parent_tracker = _parent_tracker + 2
            print('added 2 parents')

        elif data.df_fam.parents.values[famid] == 3:
            model.Add(sum(
                shifts[_parent_tracker, j] + shifts[_parent_tracker + 1, j] + shifts[_parent_tracker + 2, j] for j in
                all_days) <= data.np_presence_req_per_fam[famid])
            _parent_tracker = _parent_tracker + 3
            print('added 3 parents')

        elif data.df_fam.parents.values[famid] == 4:
            model.Add(sum(
                shifts[_parent_tracker, j] + shifts[_parent_tracker + 1, j] + shifts[_parent_tracker + 2, j] + shifts[
                    _parent_tracker + 3, j] for j in all_days) <= data.np_presence_req_per_fam[famid])
            _parent_tracker = _parent_tracker + 4
            print('added 4 parents')

        elif data.df_fam.parents.values[famid] == 5:
            model.Add(sum(
                shifts[_parent_tracker, j] + shifts[_parent_tracker + 1, j] + shifts[_parent_tracker + 2, j] + shifts[
                    _parent_tracker + 3, j] + shifts[_parent_tracker + 4, j] for j in all_days) <=
                      data.np_presence_req_per_fam[famid])
            _parent_tracker = _parent_tracker + 5
            print('added 5 parents')

        else:
            raise 'error, too many parents in one family, max 5'
    del _parent_tracker

    # Constraint 3 : parents only on days they can be present.
    for i in all_parents:
        for j in all_days:
            model.Add(shifts[i, j] <= data.np_availbool[i][j])

    # Constraint 4 : limit number of days for certain parents (maxdays)
    for _parent in all_parents:
        if not (pd.isna(data.df_parent.maxdays[_parent])):
            model.Add(sum(shifts[_parent, j] for j in all_days) <= data.df_parent.maxdays[_parent])

    # constraint 5 : set a minimum number of days for a parent
    for _parent in all_parents:
        if not (pd.isna(data.df_parent.mindays[_parent])):
            model.Add(sum(shifts[_parent, j] for j in all_days) >= data.df_parent.mindays[_parent])
    # constraint 6 : set some values fixed
    for i in all_parents:
        for j in all_days:
            if not (math.isnan(data.np_avail_fixed_bool[i][j])):
                print('added a fixed date')
                model.Add(shifts[i, j] == int(data.np_avail_fixed_bool[i][j] * 1))

    print('constraints written, time to optimize')

    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    data.set_runflag('writing results')
    solver.parameters.linearization_level = 0
    solver.parameters.max_time_in_seconds = 60.0
    solver.parameters.enumerate_all_solutions = True
    solution_limit = 100000
    resultstokeep = 10  # how many solutions should be used

    solution_printer = SolutionPrinter(resultstokeep, shifts, data.num_parents, data.num_days,
                                       solution_limit, data.np_costmatrix)
    print('running solver')
    solver.Solve(model, solution_printer)
    print('solver ran')
    solution_printer.optimal_solution()

    # Statistics.
    print('\nStatistics')
    print('  - conflicts      : %i' % solver.NumConflicts())
    print('  - branches       : %i' % solver.NumBranches())
    print('  - wall time      : %f s' % solver.WallTime())
    print('  - solutions found: %i' % solution_printer.solution_count())

    print('ended')

    if solution_printer.solution_count() == 0:
        return 'geen oplossingen'
    else:
        results = solution_printer.top_results()
        data.write_results(results['optimization_value'],
                           results['solutions'])
        return str(solution_printer.solution_count()) + ' oplossingen'
