# ===============================================================================
# Copyright (C) 2014 Ryan Holmes
#
# This file is part of eos.
#
# eos is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# eos is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with eos.  If not, see <http://www.gnu.org/licenses/>.
# ===============================================================================

import math
import re

from logbook import Logger

import eos.db


pyfalog = Logger(__name__)


class TargetProfile:
    # also determined import/export order - VERY IMPORTANT
    DAMAGE_TYPES = ("em", "thermal", "kinetic", "explosive")

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def update(self, emAmount=0, thermalAmount=0, kineticAmount=0, explosiveAmount=0, maxVelocity=None, signatureRadius=None, radius=None):
        self.emAmount = emAmount
        self.thermalAmount = thermalAmount
        self.kineticAmount = kineticAmount
        self.explosiveAmount = explosiveAmount
        self._maxVelocity = maxVelocity
        self._signatureRadius = signatureRadius
        self._radius = radius

    _idealTarget = None

    @classmethod
    def getIdeal(cls):
        if cls._idealTarget is None:
            cls._idealTarget = cls(
                emAmount=0,
                thermalAmount=0,
                kineticAmount=0,
                explosiveAmount=0,
                maxVelocity=0,
                signatureRadius=None,
                radius=0)
            cls._idealTarget.name = 'Ideal Target'
            cls._idealTarget.ID = -1
        return cls._idealTarget

    @property
    def maxVelocity(self):
        return self._maxVelocity or 0

    @maxVelocity.setter
    def maxVelocity(self, val):
        self._maxVelocity = val

    @property
    def signatureRadius(self):
        if self._signatureRadius is None or self._signatureRadius == -1:
            return math.inf
        return self._signatureRadius

    @signatureRadius.setter
    def signatureRadius(self, val):
        if val is not None and math.isinf(val):
            val = None
        self._signatureRadius = val

    @property
    def radius(self):
        return self._radius or 0

    @radius.setter
    def radius(self, val):
        self._radius = val

    @classmethod
    def importPatterns(cls, text):
        lines = re.split('[\n\r]+', text)
        patterns = []
        numPatterns = 0

        # When we import damage profiles, we create new ones and update old ones. To do this, get a list of current
        # patterns to allow lookup
        lookup = {}
        current = eos.db.getTargetProfileList()
        for pattern in current:
            lookup[pattern.name] = pattern

        for line in lines:
            try:
                if line.strip()[0] == "#":  # comments
                    continue
                line = line.split('#', 1)[0]  # allows for comments
                type, data = line.rsplit('=', 1)
                type, data = type.strip(), [d.strip() for d in data.split(',')]
            except:
                pyfalog.warning("Data isn't in correct format, continue to next line.")
                continue

            if type not in ("TargetProfile", "TargetResists"):
                continue

            numPatterns += 1
            name, dataRes, dataMisc = data[0], data[1:5], data[5:8]
            fields = {}

            for index, val in enumerate(dataRes):
                val = float(val) if val else 0
                if math.isinf(val):
                    val = 0
                try:
                    assert 0 <= val <= 100
                    fields["%sAmount" % cls.DAMAGE_TYPES[index]] = val / 100
                except:
                    pyfalog.warning("Caught unhandled exception in import patterns.")
                    continue

            if len(dataMisc) == 3:
                for index, val in enumerate(dataMisc):
                    try:
                        fieldName = ("maxVelocity", "signatureRadius", "radius")[index]
                    except IndexError:
                        break
                    val = float(val) if val else 0
                    if fieldName != "signatureRadius" and math.isinf(val):
                        val = 0
                    fields[fieldName] = val

            if len(fields) in (4, 7):  # Avoid possible blank lines
                if name.strip() in lookup:
                    pattern = lookup[name.strip()]
                    pattern.update(**fields)
                    eos.db.save(pattern)
                else:
                    pattern = TargetProfile(**fields)
                    pattern.name = name.strip()
                    eos.db.save(pattern)
                patterns.append(pattern)

        eos.db.commit()

        return patterns, numPatterns

    EXPORT_FORMAT = "TargetProfile = %s,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n"

    @classmethod
    def exportPatterns(cls, *patterns):
        out = "# Exported from pyfa\n#\n"
        out += "# Values are in following format:\n"
        out += "# TargetProfile = [name],[EM %],[Thermal %],[Kinetic %],[Explosive %],[Max velocity m/s],[Signature radius m],[Radius m]\n\n"
        for dp in patterns:
            out += cls.EXPORT_FORMAT % (
                dp.name,
                dp.emAmount * 100,
                dp.thermalAmount * 100,
                dp.kineticAmount * 100,
                dp.explosiveAmount * 100,
                dp.maxVelocity,
                dp.signatureRadius,
                dp.radius
            )

        return out.strip()

    def __deepcopy__(self, memo):
        p = TargetProfile(
            self.emAmount, self.thermalAmount, self.kineticAmount, self.explosiveAmount,
            self._maxVelocity, self._signatureRadius, self._radius)
        p.name = "%s copy" % self.name
        return p
