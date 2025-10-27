import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
from typing import Callable
import Question_1_suman as su

def house_heat_equation(T_in_0:float, gpr, T_out:Callable, R_total:float, volume:float, time_step:float, time_end:float) -> np.ndarray:
    # Constants
    T_in = T_in_0
    #specific heat of air = 1.005 kJ/kg*K
    c=1.005
    #density of air = 1.225 kg/m^3
    rho=1.225
    time_step = time_step
    time_end = time_end
    time = np.arange(0, time_end, time_step)
    T = np.zeros(len(time))
    T[0] = T_in

    # Solve the differential equation using Euler's method:
    # Runge-Kutta 4th order method for
    # dT/dt = -(T - T_out(t)) / (rho * volume * c * R_total)
    dt = time_step
    def f(t, T_val):
        return -(T_val - T_out(gpr, t)) / (rho * volume * c * R_total)
    
    for i in range(len(time) - 1):
        print(T[i])
        k1 = dt * f(time[i], T[i])
        k2 = dt * f(time[i] + dt / 2, T[i] + k1 / 2)
        k3 = dt * f(time[i] + dt / 2, T[i] + k2 / 2)
        k4 = dt * f(time[i] + dt, T[i] + k3)
        T[i + 1] = T[i] + (k1 + 2 * k2 + 2 * k3 + k4) / 6
    return T, time


def local_sensitivity_analysis(T_in_0, gpr, T_out, R_total, volume, time_step, time_end):
    variations = [0.9, 1.1]  # 10% decrease and increase
    parameters = {'R_total': R_total, 'Volume': volume, 'Initial_T_in': T_in_0}
    
    plt.figure(figsize=(10, 6))
    
    # Plot the baseline case once
    T_baseline, time = house_heat_equation(T_in_0, gpr, T_out, R_total, volume, time_step, time_end)
    plt.plot(time, T_baseline, label='Baseline 100%', linestyle='dashed', linewidth=2)
    
    for param, base_value in parameters.items():
        for factor in variations:
            new_value = base_value * factor
            if param == 'R_total':
                T_final, time = house_heat_equation(T_in_0, gpr, T_out, new_value, volume, time_step, time_end)
            elif param == 'Initial_T_in':
                T_final, time = house_heat_equation(new_value, gpr, T_out, R_total, volume, time_step, time_end)
            
            plt.plot(time, T_final, label=f'{param} {factor * 100:.0f}%')
    
    plt.xlabel('Time (hours)')
    plt.ylabel('Indoor Temperature (°C)')
    plt.title('Local Sensitivity Analysis of Indoor Temperature')
    plt.legend()
    plt.grid()
    plt.show()

def main():
    gpr = su.init_model()
    #plot the T values with respect to time
    sq_meters = 88
    #assume perimeter is a square
    perimeter = 4 * np.sqrt(sq_meters)
    #average height of house is 3 meters
    height = 3
    surface_area = perimeter * height
    volume = sq_meters * height
    R_avg = 2.5
    R_total = R_avg / surface_area
    #inital temperature
    T_in_0 = su.Tout(gpr, 0)
    
    local_sensitivity_analysis(T_in_0, gpr, su.Tout, R_total, volume, 0.05, 24)

if __name__ == '__main__':
    start_time = time.time()
    main()
    print('Elapsed Time: ', time.time() - start_time)
