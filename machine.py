from datetime import datetime, timedelta

from influxdb_client import Point
import random


class Machine:
    def __init__(self, now: datetime, config, name: str):
        self._name = name

        self._last_exec = now

        self._mode = 0
        self._mode_change_time = now

        self._modes = config['modes']

        # активная мощность
        self.p_base = config['electricity']['p']['base']
        self.p_var = config['electricity']['p']['var']
        self.p_delay = timedelta(seconds=config['electricity']['p']['delay'])

        self._p_current = self.p_base
        self._p_target = self.p_base
        self._p_current_delay = timedelta()

        # потребленная активная ээ
        self._ep_imp = 0.0

    def __str__(self):
        s = ''
        s = s.join(f'name: {self._name}')
        return s

    def cycle(self, now: datetime):
        # delta time
        current = now
        delta = current - self._last_exec
        self._last_exec = current

        points = []

        if now > self._mode_change_time:
            p_all = 0
            p = []
            for m in self._modes:
                p_all += m['prob']

            p_cumsum = 0
            for m in self._modes:
                p_cumsum += m['prob'] / p_all
                p.append(p_cumsum)

            r = random.random()
            for i in range(len(p)):
                if r < p[i]:
                    self._mode = i
                    break
            r = random.random()
            time = self._modes[self._mode]['time_base'] * (r + 1) + self._modes[self._mode]['time_var'] * (r - 1)
            self._mode_change_time += timedelta(minutes=time)

        # active power
        if (self._p_target == self.p_base or self._p_current_delay >= self.p_delay or
                (self.p_base < self._p_target < self._p_current) or
                (self.p_base > self._p_target > self._p_current)):
            self._p_target = self.p_var * (2 * random.random() - 1) + self.p_base
            self._p_current_delay = timedelta()

        self._p_current += delta.total_seconds() / self.p_delay.total_seconds() * (self._p_target - self.p_base)
        self._p_current_delay += delta

        p_current_mode = self._p_current * self._modes[self._mode]['elec_coef']

        if self._p_current > 0:
            self._ep_imp += abs(p_current_mode) * delta.total_seconds() / 3600
        elif self._p_current < 0:
            self._ep_exp += abs(p_current_mode) * delta.total_seconds() / 3600

        points.extend([
            Point(self._name)
                .field("mode", self._modes[self._mode]['name'])
                .time(now)
                .tag('datatype', 'string'),
            Point(self._name)
                .field("p", p_current_mode)
                .time(now)
                .tag('datatype', 'float')
                .tag('aggfunc', 'mean'),
            Point(self._name)
                .field("ep_imp", self._ep_imp)
                .time(now)
                .tag('datatype', 'int')
                .tag('aggfunc', 'increase'),
        ])

        return points
