# =============================================================================
# Copyright (C) 2010 Diego Duclos
#
# This file is part of pyfa.
#
# pyfa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyfa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyfa.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================


import math

from graphs.data.base import SmoothPointGetter


class Time2SpeedGetter(SmoothPointGetter):

    def _getCommonData(self, miscParams, src, tgt):
        return {
            'maxSpeed': src.getMaxVelocity(),
            'mass': src.item.ship.getModifiedItemAttr('mass'),
            'agility': src.item.ship.getModifiedItemAttr('agility')}

    def _calculatePoint(self, x, miscParams, src, tgt, commonData):
        time = x
        maxSpeed = commonData['maxSpeed']
        mass = commonData['mass']
        agility = commonData['agility']
        # https://wiki.eveuniversity.org/Acceleration#Mathematics_and_formulae
        speed = maxSpeed * (1 - math.exp((-time * 1000000) / (agility * mass)))
        return speed


class Time2DistanceGetter(SmoothPointGetter):

    def _getCommonData(self, miscParams, src, tgt):
        return {
            'maxSpeed': src.getMaxVelocity(),
            'mass': src.item.ship.getModifiedItemAttr('mass'),
            'agility': src.item.ship.getModifiedItemAttr('agility')}

    def _calculatePoint(self, x, miscParams, src, tgt, commonData):
        time = x
        maxSpeed = commonData['maxSpeed']
        mass = commonData['mass']
        agility = commonData['agility']
        # Definite integral of:
        # https://wiki.eveuniversity.org/Acceleration#Mathematics_and_formulae
        distance_t = maxSpeed * time + (maxSpeed * agility * mass * math.exp((-time * 1000000) / (agility * mass)) / 1000000)
        distance_0 = maxSpeed * 0 + (maxSpeed * agility * mass * math.exp((-0 * 1000000) / (agility * mass)) / 1000000)
        distance = distance_t - distance_0
        return distance
