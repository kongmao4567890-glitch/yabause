package org.uoyabause.android

import android.content.Context
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.TextView
import androidx.core.widget.doAfterTextChanged
import androidx.preference.PreferenceDialogFragmentCompat
import org.devmiyax.yabasanshiro.R

class SpeedLimitDialogFragment : PreferenceDialogFragmentCompat() {
    private var selectedPercent = SpeedLimitValue.NORMAL
    private var unlimited = false
    private lateinit var input: EditText

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val current = (preference as SpeedLimitPreference).percent
        selectedPercent = savedInstanceState?.getInt("percent")
            ?: if (current == SpeedLimitValue.UNLIMITED) SpeedLimitValue.NORMAL else current
        unlimited = savedInstanceState?.getBoolean("unlimited")
            ?: (current == SpeedLimitValue.UNLIMITED)
    }

    override fun onCreateDialogView(context: Context): View {
        val padding = (24 * context.resources.displayMetrics.density).toInt()
        val layout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding / 2, padding, padding / 2)
        }
        layout.addView(TextView(context).apply { setText(R.string.speed_limit_help) })
        val valueLabel = TextView(context).apply {
            textSize = 24f
            text = if (unlimited) context.getString(R.string.speed_limit_unlimited)
                else context.getString(R.string.speed_limit_percent, selectedPercent)
        }
        layout.addView(valueLabel)
        input = EditText(context).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            setSingleLine(true)
            setSelectAllOnFocus(true)
            contentDescription = context.getString(R.string.frameLimit)
            setText(selectedPercent.toString())
        }
        layout.addView(input)
        val slider = SeekBar(context).apply {
            max = SpeedLimitValue.MAX - SpeedLimitValue.MIN
            keyProgressIncrement = 1
            progress = selectedPercent - SpeedLimitValue.MIN
            contentDescription = context.getString(R.string.speed_limit_percent, selectedPercent)
        }
        layout.addView(slider)
        val unlimitedBox = CheckBox(context).apply {
            setText(R.string.speed_limit_unlimited)
            isChecked = unlimited
        }
        layout.addView(unlimitedBox)
        layout.addView(Button(context).apply {
            setText(R.string.speed_limit_reset)
            setOnClickListener {
                unlimitedBox.isChecked = false
                input.setText(SpeedLimitValue.NORMAL.toString())
            }
        })
        slider.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar, progress: Int, fromUser: Boolean) {
                if (fromUser) input.setText((progress + SpeedLimitValue.MIN).toString())
            }
            override fun onStartTrackingTouch(seekBar: SeekBar) {}
            override fun onStopTrackingTouch(seekBar: SeekBar) {}
        })
        input.doAfterTextChanged { text ->
            val percent = text?.toString()?.toIntOrNull()
            if (percent == null || percent !in SpeedLimitValue.MIN..SpeedLimitValue.MAX) {
                input.error = getString(R.string.speed_limit_range)
            } else {
                input.error = null
                selectedPercent = percent
                valueLabel.text = getString(R.string.speed_limit_percent, percent)
                slider.progress = percent - SpeedLimitValue.MIN
                slider.contentDescription = getString(R.string.speed_limit_percent, percent)
            }
        }
        unlimitedBox.setOnCheckedChangeListener { _, checked ->
            unlimited = checked
            valueLabel.text = if (checked) getString(R.string.speed_limit_unlimited)
                else getString(R.string.speed_limit_percent, selectedPercent)
            input.isEnabled = !checked
            slider.isEnabled = !checked
        }
        input.isEnabled = !unlimited
        slider.isEnabled = !unlimited
        return ScrollView(context).apply { addView(layout) }
    }

    override fun onStart() {
        super.onStart()
        // Validate before dismissing; invalid input must not silently save the previous value.
        (dialog as? androidx.appcompat.app.AlertDialog)
            ?.getButton(android.content.DialogInterface.BUTTON_POSITIVE)?.setOnClickListener {
                val percent = input.text.toString().toIntOrNull()
                if (!unlimited && (percent == null || percent !in SpeedLimitValue.MIN..SpeedLimitValue.MAX)) {
                    input.error = getString(R.string.speed_limit_range)
                } else {
                    (preference as SpeedLimitPreference).save(
                        if (unlimited) SpeedLimitValue.UNLIMITED else percent!!
                    )
                    dismiss()
                }
            }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putInt("percent", selectedPercent)
        outState.putBoolean("unlimited", unlimited)
    }

    override fun onDialogClosed(positiveResult: Boolean) {
        // Saved by the validated positive-button handler. Cancel leaves preferences untouched.
    }

    companion object {
        fun newInstance(key: String) = SpeedLimitDialogFragment().apply {
            arguments = Bundle().apply { putString("key", key) }
        }
    }
}
