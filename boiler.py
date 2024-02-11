#!/usr/bin/env python
import random
import time

from simple_pid import PID
import plotext as plt


class Boiler:
    """
    Simple simulation of a water boiler which can heat up water
    and where the heat dissipates slowly over time
    """

    def __init__(self):
        self.water_temp = 20

    def update(self, boiler_power, dt):
        if boiler_power > 0:
            # Boiler can only produce heat, not cold
            self.water_temp += 1 * boiler_power * dt

        # Some heat dissipation
        self.water_temp -= dt * random.randrange(5, 20)
        return self.water_temp


if __name__ == '__main__':
    boiler = Boiler()
    water_temp = boiler.water_temp

    pid = PID(5, 0.01, 0.1, setpoint=water_temp)
    pid.output_limits = (0, 30)

    start_time = time.time()
    last_time = start_time

    # Keep track of values for plotting
    powers, setpoint, y, x = [], [], [], []

    while time.time() - start_time < 10:
        time.sleep(0.1)
        current_time = time.time()
        date_two = current_time - last_time

        power = round(pid(water_temp), 4)
        water_temp = boiler.update(power, date_two)
        print(f'water_temp={water_temp} power={power}')

        x += [current_time - start_time]
        y += [water_temp]
        setpoint += [pid.setpoint]
        powers += [power]

        if current_time - start_time > 1:
            pid.setpoint = 100

        last_time = current_time

    plt.plot(x, powers)
    plt.scatter(x, y)
    # plt.plot(setpoint)
    plt.plotsize(300, 30)
    plt.show()
