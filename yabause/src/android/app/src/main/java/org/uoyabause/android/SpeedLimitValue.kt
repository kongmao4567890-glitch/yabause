package org.uoyabause.android

/** Keep the existing string key so global and Harmony per-game stores remain compatible. */
object SpeedLimitValue {
    const val MIN = 1
    const val MAX = 2000
    const val NORMAL = 100
    const val UNLIMITED = 0
    private const val PREFIX = "percent:"

    fun decode(value: String?): Int {
        if (value?.startsWith(PREFIX) == true) {
            val percent = value.removePrefix(PREFIX).toIntOrNull() ?: return NORMAL
            return if (percent == UNLIMITED) UNLIMITED else percent.coerceIn(MIN, MAX)
        }
        return when (val mode = value?.toIntOrNull() ?: 0) {
            1 -> UNLIMITED
            in 2..14 -> (mode + 2) * 50
            15 -> 1000
            16 -> 2000
            else -> NORMAL
        }
    }

    fun encode(percent: Int): String = PREFIX +
        if (percent == UNLIMITED) UNLIMITED else percent.coerceIn(MIN, MAX)

    /** Nonnegative values retain the native legacy enum; negative values carry a percentage. */
    fun nativeMode(value: String?): Int = when (val percent = decode(value)) {
        UNLIMITED -> 1
        NORMAL -> 0
        else -> -percent
    }
}
