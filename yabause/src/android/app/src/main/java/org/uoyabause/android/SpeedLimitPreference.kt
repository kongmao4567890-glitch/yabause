package org.uoyabause.android

import android.content.Context
import android.util.AttributeSet
import androidx.preference.DialogPreference
import androidx.preference.Preference
import org.devmiyax.yabasanshiro.R

class SpeedLimitPreference(context: Context, attrs: AttributeSet?) : DialogPreference(context, attrs) {
    init {
        setPositiveButtonText(android.R.string.ok)
        setNegativeButtonText(android.R.string.cancel)
        summaryProvider = Preference.SummaryProvider<SpeedLimitPreference> { preference ->
            val percent = preference.percent
            if (percent == SpeedLimitValue.UNLIMITED) context.getString(R.string.speed_limit_unlimited)
            else context.getString(R.string.speed_limit_percent, percent)
        }
    }

    val percent: Int
        get() = SpeedLimitValue.decode(getPersistedString("0"))

    fun save(percent: Int) {
        val value = SpeedLimitValue.encode(percent)
        if (callChangeListener(value)) {
            persistString(value)
            notifyChanged()
        }
    }
}
