package org.uoyabause.android

import org.junit.Assert.assertEquals
import org.junit.Test

class SpeedLimitValueTest {
    @Test fun legacySettingsKeepTheirSpeed() {
        val speeds = listOf(100, 0, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 1000, 2000)
        speeds.forEachIndexed { mode, percent ->
            assertEquals(percent, SpeedLimitValue.decode(mode.toString()))
        }
    }

    @Test fun everyPercentageRoundTripsWithoutEnumCollisions() {
        for (percent in 0..2000) {
            val stored = SpeedLimitValue.encode(percent)
            assertEquals(percent, SpeedLimitValue.decode(stored))
            assertEquals(when (percent) { 0 -> 1; 100 -> 0; else -> -percent }, SpeedLimitValue.nativeMode(stored))
        }
    }

    @Test fun invalidSettingsFallBackAndOutOfRangePercentagesAreClamped() {
        for (value in listOf(null, "", "bad", "99", "percent:bad", "percent:999999999999")) {
            assertEquals(100, SpeedLimitValue.decode(value))
        }
        assertEquals(1, SpeedLimitValue.decode("percent:-10"))
        assertEquals(2000, SpeedLimitValue.decode("percent:2500"))
    }
}
