import numpy as np
import matplotlib.pyplot as plt
import time
from SALib.sample import sobol
from SALib.analyze import sobol as sobol_analyze
import Question_1_suman as su

def house_heat_equation(T_in_0, gpr, T_out, R_total, volume, time_step, time_end):
    c = 1.005  # Specific heat of air (kJ/kg*K)
    rho = 1.225  # Density of air (kg/m^3)
    time = np.arange(0, time_end, time_step)
    T = np.zeros(len(time))
    T[0] = T_in_0
    
    def f(t, T_val):
        return -(T_val - T_out(gpr, t)) / max(rho * volume * c * R_total, 1e-6)
    
    dt = time_step
    for i in range(len(time) - 1):
        k1 = dt * f(time[i], T[i])
        k2 = dt * f(time[i] + dt / 2, T[i] + k1 / 2)
        k3 = dt * f(time[i] + dt / 2, T[i] + k2 / 2)
        k4 = dt * f(time[i] + dt, T[i] + k3)
        T[i + 1] = T[i] + (k1 + 2 * k2 + 2 * k3 + k4) / 6
    
    return T[-1]  # Return final temperature

def global_sensitivity_analysis():
    gpr = su.init_model()
    sq_meters = 88
    perimeter = 4 * np.sqrt(sq_meters)
    height = 3
    surface_area = perimeter * height
    volume = sq_meters * height
    R_avg = 2.5
    R_total = R_avg / surface_area
    T_in_0 = su.Tout(gpr, 0)
    
    problem = {
        'num_vars': 3,
        'names': ['R_total', 'Volume', 'Initial_T_in'],
        'bounds': [[R_total * 0.8, R_total * 1.2],  # Vary by ±20%
                   [volume * 0.8, volume * 1.2],
                   [T_in_0 * 0.8, T_in_0 * 1.2]]
    }
    
    param_values = sobol.sample(problem, 256)  # Reduce samples for faster testing
    print("Generated parameter samples:", param_values[:5])  # Debugging output
    
    results = []
    for row in param_values:
        print(f"Running with R_total={row[0]:.4f}, Volume={row[1]:.2f}, Initial_T_in={row[2]:.2f}")  # Debugging
        results.append(house_heat_equation(row[2], gpr, su.Tout, row[0], row[1], 0.05, 24))
    results = np.array(results)
    
    print("Results sample:", results[:10])
    print("NaN count:", np.isnan(results).sum(), "Inf count:", np.isinf(results).sum())
    
    if np.var(results) == 0:
        print("Warning: No variation in results, Sobol analysis will fail.")
        return
    
    si = sobol_analyze.analyze(problem, results)
    
    print("Sobol Sensitivity Indices:")
    for i, name in enumerate(problem['names']):
        print(f"{name} - S1: {si['S1'][i]:.4f}, ST: {si['ST'][i]:.4f}")
    
    plt.figure(figsize=(8, 6))
    plt.bar(problem['names'], si['ST'], color='skyblue', edgecolor='black')
    plt.xlabel('Parameter')
    plt.ylabel('Total Sensitivity Index')
    plt.title('Global Sensitivity Analysis (Sobol Method)')
    plt.show()

if __name__ == '__main__':
    start_time = time.time()
    global_sensitivity_analysis()
    print('Elapsed Time:', time.time() - start_time)



##main changes from local sensitivity code is using sobol method for global sensitivity analysis
##and using max(_, 1e-6) to prevent division by zero error for Tin and R_total