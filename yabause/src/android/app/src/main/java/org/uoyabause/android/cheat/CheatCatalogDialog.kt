package org.uoyabause.android.cheat

import android.app.Dialog
import android.content.DialogInterface
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.DialogFragment
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.devmiyax.yabasanshiro.R
import org.uoyabause.android.YabauseStorage

/** Search only chooses source material; imports always belong to the active game's ID. */
class CheatCatalogDialog : DialogFragment() {
    private var catalog: CheatCatalog? = null
    private var selectedGameId: String? = null
    private val checked = linkedSetOf<Int>()
    private var busy = false
    private lateinit var search: EditText
    private lateinit var status: TextView
    private lateinit var back: Button
    private lateinit var list: ListView
    private var resultGames = emptyList<CatalogGame>()
    private var rowAdapter: BaseAdapter? = null
    private val targetGame get() = requireArguments().getString(ARG_GAME).orEmpty()
    private val selectedGame get() = catalog?.games?.find { it.id == selectedGameId }

    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        selectedGameId = savedInstanceState?.getString("selected")
        checked.addAll(savedInstanceState?.getIntArray("checked")?.toList().orEmpty())
        val ctx = requireContext()
        val padding = (16 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding / 2, padding, 0)
        }
        root.addView(TextView(ctx).apply { text = getString(R.string.cheat_catalog_target, targetGame) })
        search = EditText(ctx).apply {
            hint = getString(R.string.cheat_catalog_hint)
            setSingleLine(true)
            setText(savedInstanceState?.getString("query") ?: targetGame)
        }
        root.addView(search)
        back = Button(ctx).apply {
            setText(R.string.cheat_catalog_back)
            setOnClickListener { selectedGameId = null; checked.clear(); refresh() }
        }
        root.addView(back)
        status = TextView(ctx).apply { setPadding(0, padding / 2, 0, padding / 2) }
        root.addView(status)
        list = ListView(ctx)
        root.addView(list, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        rowAdapter = object : BaseAdapter() {
            override fun getCount() = selectedGame?.let { it.cheats.size + if (it.notes.isNotBlank()) 1 else 0 } ?: resultGames.size
            override fun getItem(position: Int): Any = selectedGame?.cheats?.getOrNull(position) ?: position
            override fun getItemId(position: Int) = position.toLong()
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                val game = selectedGame
                val entry = game?.cheats?.getOrNull(position)
                return CheckedTextView(ctx).apply {
                    setPadding(padding / 2, padding, padding / 2, padding)
                    textSize = 16f
                    minimumHeight = (56 * resources.displayMetrics.density).toInt()
                    when {
                        game == null -> {
                            val item = resultGames[position]
                            text = "${item.name}\n" + getString(R.string.cheat_catalog_game_count, item.availableCount) + " · ${item.source}"
                        }
                        entry == null -> text = getString(R.string.cheat_catalog_notes)
                        else -> {
                            text = entry.title + if (!entry.importable) "\n" + getString(R.string.cheat_catalog_reference) else ""
                            if (entry.importable) setCheckMarkDrawable(android.R.drawable.checkbox_on_background)
                            isChecked = checked.contains(position)
                            // Use a stateful drawable, with explicit check state for keyboard and touch.
                            if (entry.importable) setCheckMarkDrawable(
                                if (isChecked) android.R.drawable.checkbox_on_background else android.R.drawable.checkbox_off_background)
                        }
                    }
                }
            }
        }
        list.adapter = rowAdapter
        list.setOnItemClickListener { _, _, position, _ ->
            if (!busy) {
                val game = selectedGame
                if (game == null) {
                    selectedGameId = resultGames[position].id
                    checked.clear()
                    search.clearFocus()
                    (ctx.getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager)
                        .hideSoftInputFromWindow(search.windowToken, 0)
                    refresh()
                    list.setSelection(0)
                } else {
                    val entry = game.cheats.getOrNull(position)
                    if (entry?.importable == true) {
                        if (!checked.add(position)) checked.remove(position)
                        refresh()
                    } else showReference(entry?.title ?: game.name, entry?.raw ?: game.notes,
                        if (entry == null) null else getString(if (entry.reason == "unsupported")
                            R.string.cheat_catalog_unsupported else R.string.cheat_catalog_incomplete))
                }
            }
        }
        list.setOnItemLongClickListener { _, _, position, _ ->
            selectedGame?.cheats?.getOrNull(position)?.let { showReference(it.title, it.raw, null) }
            true
        }
        search.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { refresh() }
            override fun afterTextChanged(s: Editable?) {}
        })
        val dialog = AlertDialog.Builder(ctx).setTitle(R.string.cheat_catalog_title).setView(root)
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.cheat_catalog_add, null).create()
        lifecycleScope.launch {
            try {
                val loaded = withContext(Dispatchers.IO) {
                    ctx.assets.open("cheats/catalog.json").bufferedReader(Charsets.UTF_8).use { CheatCatalog.fromJson(it.readText()) }
                }
                catalog = loaded
                if (selectedGame == null) selectedGameId = null
                checked.removeAll { selectedGame?.cheats?.getOrNull(it)?.importable != true }
                refresh()
            } catch (e: Exception) {
                if (isAdded) status.setText(R.string.cheat_catalog_load_failed)
            }
        }
        refresh()
        return dialog
    }

    override fun onStart() {
        super.onStart()
        dialog?.window?.apply {
            setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
            setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        }
        (dialog as? AlertDialog)?.getButton(DialogInterface.BUTTON_POSITIVE)?.setOnClickListener { importSelected() }
        refresh()
    }

    private fun refresh() {
        if (!::search.isInitialized) return
        val game = selectedGame
        search.visibility = if (game == null) View.VISIBLE else View.GONE
        back.visibility = if (game == null) View.GONE else View.VISIBLE
        back.isEnabled = !busy
        if (catalog == null) status.setText(R.string.cheat_catalog_loading)
        else if (game == null) {
            resultGames = catalog!!.search(search.text.toString())
            status.text = if (resultGames.isEmpty()) getString(R.string.cheat_catalog_empty)
                else getString(R.string.cheat_catalog_results, resultGames.size)
        } else status.text = "${game.name}\n" + getString(R.string.cheat_catalog_selected, checked.size)
        rowAdapter?.notifyDataSetChanged()
        (dialog as? AlertDialog)?.getButton(DialogInterface.BUTTON_POSITIVE)?.isEnabled =
            !busy && targetGame.isNotBlank() && checked.isNotEmpty()
    }

    private fun showReference(title: String, content: String, reason: String?) {
        val text = TextView(requireContext()).apply {
            setPadding(24, 16, 24, 16)
            setTextIsSelectable(true)
            this.text = listOfNotNull(reason, content).joinToString("\n\n")
        }
        AlertDialog.Builder(requireContext()).setTitle(title)
            .setView(ScrollView(requireContext()).apply { addView(text) })
            .setPositiveButton(android.R.string.ok, null).show()
    }

    private fun importSelected() {
        if (busy || targetGame.isBlank()) return
        val game = selectedGame ?: return
        val entries = checked.mapNotNull { game.cheats.getOrNull(it) }.filter { it.importable }
        if (entries.isEmpty()) return
        val target = targetGame
        busy = true
        isCancelable = false
        (dialog as? AlertDialog)?.getButton(DialogInterface.BUTTON_NEGATIVE)?.isEnabled = false
        refresh()
        lifecycleScope.launch {
            try {
                val count = withContext(Dispatchers.IO) { CheatCatalogImport.insert(target, entries) }
                if (isAdded) {
                    parentFragmentManager.setFragmentResult(RESULT, Bundle().apply { putString(ARG_GAME, target) })
                    Toast.makeText(requireContext(), getString(R.string.cheat_catalog_added, count, entries.size - count), Toast.LENGTH_LONG).show()
                    dismiss()
                }
            } catch (e: Exception) {
                if (isAdded) Toast.makeText(requireContext(), R.string.cheat_catalog_import_failed, Toast.LENGTH_LONG).show()
            } finally {
                busy = false
                isCancelable = true
                (dialog as? AlertDialog)?.getButton(DialogInterface.BUTTON_NEGATIVE)?.isEnabled = true
                if (isAdded) refresh()
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putString("selected", selectedGameId)
        outState.putString("query", search.text.toString())
        outState.putIntArray("checked", checked.toIntArray())
    }

    companion object {
        const val RESULT = "cheat-catalog-imported"
        const val ARG_GAME = "gameid"
        fun newInstance(gameId: String) = CheatCatalogDialog().apply {
            arguments = Bundle().apply { putString(ARG_GAME, gameId) }
        }
    }
}

internal object CheatCatalogImport {
    fun insert(gameId: String, entries: List<CatalogCheat>): Int {
        require(gameId.isNotBlank())
        var count = 0
        YabauseStorage.db.runInTransaction {
            val dao = YabauseStorage.cheatDao
            val existing = dao.selectLocal(gameId).map { CatalogCheat.codeKey(it.cheat_code.orEmpty()) }.toMutableSet()
            for (entry in entries) {
                if (entry.importable && existing.add(CatalogCheat.codeKey(entry.code))) {
                    dao.insert(Cheat(gameId, entry.title, entry.code)) // Disabled until explicitly enabled locally.
                    count++
                }
            }
        }
        return count
    }
}
