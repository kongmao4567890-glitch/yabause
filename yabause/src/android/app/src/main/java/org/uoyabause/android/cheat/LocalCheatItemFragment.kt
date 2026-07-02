/*  Copyright 2019 devMiyax(smiyaxdev@gmail.com)

    This file is part of YabaSanshiro.

    YabaSanshiro is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    YabaSanshiro is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with YabaSanshiro; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
*/
package org.uoyabause.android.cheat

import android.app.AlertDialog
import android.content.Context
import android.content.DialogInterface
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.PopupMenu
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import java.io.IOException
import java.util.ArrayList
import org.devmiyax.yabasanshiro.R
import org.uoyabause.android.YabauseStorage

/**
 * A fragment representing a list of Items.
 *
 *
 * Activities containing this fragment MUST implement the [OnListFragmentInteractionListener]
 * interface.
 */
class LocalCheatItemFragment
/**
 * Mandatory empty constructor for the fragment manager to instantiate the
 * fragment (e.g. upon screen orientation changes).
 */
    : Fragment(), LocalCheatItemRecyclerViewAdapter.OnItemClickListener {
    private var mColumnCount = 1
    private var mListener: OnListFragmentInteractionListener? = null
    private var _items: ArrayList<CheatItem?>? = null
    private var _cheatMap: MutableMap<String, Cheat> = mutableMapOf()
    private var mGameCode: String? = null
    private var backcode_ = ""
    var root_view_: View? = null
    var listview_: RecyclerView? = null
    var adapter_: LocalCheatItemRecyclerViewAdapter? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    private val importFileLauncher: ActivityResultLauncher<Array<String>> =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            if (uri != null) {
                importCheatsFromFile(uri)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mColumnCount = requireArguments().getInt(ARG_COLUMN_COUNT)
        mGameCode = requireArguments().getString(ARG_GAME_ID)
        val cnv = CheatConverter()
        if (cnv.hasOldVersion()) {
            cnv.execute()
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_localcheatitem_list, container, false)
        listview_ = view.findViewById<View>(R.id.list) as RecyclerView
        val context = view.context
        listview_!!.layoutManager = LinearLayoutManager(context)
        updateCheatList()
        root_view_ = view
        val add = view.findViewById<View>(R.id.button_add) as Button
        add.setOnClickListener { _ -> onAddItem() }
        val import = view.findViewById<View>(R.id.button_import) as Button
        import.setOnClickListener { _ -> startImportCheats() }
        return view
    }

    override fun setUserVisibleHint(isVisibleToUser: Boolean) {
        super.setUserVisibleHint(isVisibleToUser)
        if (isVisibleToUser) {
            // updateCheatList();
        } else {
        }
    }

    override fun onAttach(context: Context) {
        super.onAttach(context)
        if (context is OnListFragmentInteractionListener) {
            mListener = context
        } else {
//            throw new RuntimeException(context.toString()
//                    + " must implement OnListFragmentInteractionListener");
        }
    }

    override fun onDetach() {
        super.onDetach()
        mListener = null
    }

    interface OnListFragmentInteractionListener {
        fun onListFragmentInteraction(item: CheatItem?)
    }

    fun showErrorMessage() {
        Toast.makeText(context, getString(R.string.cheat_error), Toast.LENGTH_LONG)
            .show()
    }

    /**
     * Loads the local cheats for the current game from the Room database and
     * converts them into [CheatItem] instances for display.
     *
     * The database access is performed on a background thread because Room
     * queries must not block the UI thread. The adapter is updated on the
     * main thread once the data is ready.
     */
    fun updateCheatList() {
        if (listview_ == null) {
            return
        }
        if (mGameCode == null) {
            return
        }
        val gameCode = mGameCode!!
        val frag = tabCheatFragmentInstance
        Thread {
            try {
                val cheats = YabauseStorage.cheatDao.selectLocal(gameCode)
                val items = ArrayList<CheatItem?>()
                val cheatMap = mutableMapOf<String, Cheat>()
                for (cheat in cheats) {
                    val newitem = CheatItem()
                    newitem.key = cheat.id.toString()
                    newitem.gameid = cheat.gameid ?: ""
                    newitem.description = cheat.description ?: ""
                    newitem.cheat_code = cheat.cheat_code ?: ""
                    newitem.enable = frag?.isActive(newitem.cheat_code) ?: false
                    newitem.sharedKey = ""
                    items.add(newitem)
                    cheatMap[newitem.key] = cheat
                }
                mainHandler.post {
                    _items = items
                    _cheatMap = cheatMap
                    adapter_ =
                        LocalCheatItemRecyclerViewAdapter(_items, this@LocalCheatItemFragment)
                    listview_?.adapter = adapter_
                }
            } catch (e: Exception) {
                Log.e("LocalCheatItemFragment", "updateCheatList failed", e)
                mainHandler.post { showErrorMessage() }
            }
        }.start()
    }

    val tabCheatFragmentInstance: TabCheatFragment?
        get() {
            var xFragment: TabCheatFragment? = null
            for (fragment in requireFragmentManager().fragments) {
                if (fragment is TabCheatFragment) {
                    xFragment = fragment
                    break
                }
            }
            return xFragment
        }

    override fun onItemClick(position: Int, item: CheatItem?, v: View?) {
        val popup = PopupMenu(activity, v)
        val inflate = popup.menuInflater
        inflate.inflate(R.menu.local_cheat, popup.menu)
        val cheatitem = item

        if (cheatitem == null) {
            return
        }

        popup.menu.findItem(R.id.acp_activate)?.let { mitem ->
            if (cheatitem.enable) {
                mitem.setTitle(R.string.disable)
            } else {
                mitem.setTitle(R.string.enable)
            }
        }

        popup.setOnMenuItemClickListener(PopupMenu.OnMenuItemClickListener { clickedItem ->
            when (clickedItem.itemId) {
                R.id.acp_activate -> {
                    cheatitem.enable = !cheatitem.enable
                    val frag = tabCheatFragmentInstance
                    if (frag != null) {
                        if (cheatitem.enable) {
                            frag.AddActiveCheat(cheatitem.cheat_code)
                        } else {
                            frag.RemoveActiveCheat(cheatitem.cheat_code)
                        }
                    }
                    adapter_?.notifyDataSetChanged()
                }
                R.id.acp_edit -> {
                    backcode_ = cheatitem.cheat_code
                    val newFragment = LocalCheatEditDialog()
                    newFragment.setEditTarget(cheatitem)
                    newFragment.setTargetFragment(this@LocalCheatItemFragment, EDIT_ITEM)
                    newFragment.show(requireFragmentManager(), "Cheat")
                }
                R.id.acp_import -> {
                    startImportCheats()
                }
                R.id.delete -> {
                    RemoveCheat(cheatitem)
                    adapter_?.notifyDataSetChanged()
                }
                else -> return@OnMenuItemClickListener false
            }
            false
        })
        popup.show()
    }

    fun onAddItem() {
        val newFragment = LocalCheatEditDialog()
        newFragment.setTargetFragment(this, NEW_ITEM)
        newFragment.show(requireFragmentManager(), "Cheat")
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == NEW_ITEM) {
            if (resultCode == LocalCheatEditDialog.APPLY) {
                val desc = data?.getStringExtra(LocalCheatEditDialog.DESC)
                val code = data?.getStringExtra(LocalCheatEditDialog.CODE)
                if (desc != null && code != null) {
                    val cheat = Cheat(mGameCode, desc, code)
                    Thread {
                        try {
                            YabauseStorage.cheatDao.insert(cheat)
                            mainHandler.post { updateCheatList() }
                        } catch (e: Exception) {
                            Log.e("LocalCheatItemFragment", "insert failed", e)
                            mainHandler.post { showErrorMessage() }
                        }
                    }.start()
                }
            }
        } else if (requestCode == EDIT_ITEM) {
            if (resultCode == LocalCheatEditDialog.APPLY) {
                val frag = tabCheatFragmentInstance
                frag?.RemoveActiveCheat(backcode_)
                val key = data?.getStringExtra(LocalCheatEditDialog.KEY)
                val desc = data?.getStringExtra(LocalCheatEditDialog.DESC)
                val code = data?.getStringExtra(LocalCheatEditDialog.CODE)
                val cheat = if (key != null) _cheatMap[key] else null
                if (cheat != null && desc != null && code != null) {
                    cheat.description = desc
                    cheat.cheat_code = code
                    Thread {
                        try {
                            YabauseStorage.cheatDao.update(cheat)
                            mainHandler.post { updateCheatList() }
                        } catch (e: Exception) {
                            Log.e("LocalCheatItemFragment", "update failed", e)
                            mainHandler.post { showErrorMessage() }
                        }
                    }.start()
                }
                adapter_?.notifyDataSetChanged()
            }
        }
    }

    fun RemoveCheat(cheatitem: CheatItem) {
        AlertDialog.Builder(activity)
            .setMessage(getString(R.string.are_you_sure_to_delete) + cheatitem.description + "?")
            .setPositiveButton(R.string.yes, DialogInterface.OnClickListener { _, _ ->
                val cheat = _cheatMap[cheatitem.key]
                if (cheat != null) {
                    Thread {
                        try {
                            YabauseStorage.cheatDao.delete(cheat)
                            mainHandler.post { updateCheatList() }
                        } catch (e: Exception) {
                            Log.e("LocalCheatItemFragment", "delete failed", e)
                            mainHandler.post { showErrorMessage() }
                        }
                    }.start()
                }
            })
            .setNegativeButton(R.string.no, null)
            .show()
    }

    fun Remove(index: Int) {
        val item = _items?.getOrNull(index) ?: return
        val cheat = _cheatMap[item.key]
        if (cheat != null) {
            Thread {
                try {
                    YabauseStorage.cheatDao.delete(cheat)
                    mainHandler.post { updateCheatList() }
                } catch (e: Exception) {
                    Log.e("LocalCheatItemFragment", "delete failed", e)
                    mainHandler.post { showErrorMessage() }
                }
            }.start()
        }
    }

    /**
     * Launches the system document picker so the user can select a cheat file
     * to import.
     */
    private fun startImportCheats() {
        importFileLauncher.launch(arrayOf("*/*"))
    }

    /**
     * Reads the selected file, parses the cheat codes and inserts them into the
     * Room database. The user is notified with a Toast reporting how many cheats
     * were imported (or the error that occurred).
     */
    private fun importCheatsFromFile(uri: Uri) {
        val ctx = context ?: return
        val gameCode = mGameCode
        Thread {
            try {
                val content = ctx.contentResolver.openInputStream(uri)?.use { inputStream ->
                    inputStream.bufferedReader().readText()
                } ?: throw IOException("Cannot open file")
                val parsed = parseCheats(content)
                if (parsed.isEmpty()) {
                    mainHandler.post {
                        Toast.makeText(
                            ctx,
                            getString(R.string.cheat_import_failed, "No valid cheats found"),
                            Toast.LENGTH_LONG
                        ).show()
                    }
                    return@Thread
                }
                var count = 0
                for ((desc, code) in parsed) {
                    val cheat = Cheat(gameCode, desc, code)
                    YabauseStorage.cheatDao.insert(cheat)
                    count++
                }
                val finalCount = count
                mainHandler.post {
                    Toast.makeText(
                        ctx,
                        getString(R.string.cheat_import_success, finalCount),
                        Toast.LENGTH_LONG
                    ).show()
                    updateCheatList()
                }
            } catch (e: Exception) {
                Log.e("LocalCheatItemFragment", "import failed", e)
                val msg = e.message ?: "Unknown error"
                mainHandler.post {
                    Toast.makeText(
                        ctx,
                        getString(R.string.cheat_import_failed, msg),
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }.start()
    }

    /**
     * Parses the content of an imported cheat file into a list of
     * (description, cheat_code) pairs.
     *
     * Supported formats:
     *  1. Action Replay blocks separated by blank lines. The first non-code line
     *     of a block is the description, the remaining lines are the codes. A block
     *     may contain several code lines which are joined with a newline.
     *  2. Inline format: "description|XXXXXXXX YYYY" or "description:XXXXXXXX YYYY"
     *     (one cheat per line).
     *  3. Plain list of codes (one code per line, no description). Each line
     *     becomes an individual cheat with an auto generated description "Cheat N".
     *
     * A code line matches "XXXXXXXX YYYY" where the address is 8 hex digits and
     * the value is 1 to 4 hex digits (e.g. "16000000 0063" or "36000010 01").
     */
    private fun parseCheats(content: String): List<Pair<String, String>> {
        val result = mutableListOf<Pair<String, String>>()
        val codePattern = Regex("^[0-9A-Fa-f]{8} [0-9A-Fa-f]{1,4}$")
        val inlinePattern = Regex("^(.+?)\\s*[|:]\\s*([0-9A-Fa-f]{8} [0-9A-Fa-f]{1,4})$")
        var cheatIndex = 1

        // Split into blocks separated by one or more blank lines.
        val blocks = content.split(Regex("(\\r?\\n){2,}"))

        for (block in blocks) {
            val lines = block.lines().map { it.trim() }.filter { it.isNotEmpty() }
            if (lines.isEmpty()) continue

            // Inline format: every line of the block is "desc|code" / "desc:code".
            val inlinePairs = lines.mapNotNull { line ->
                inlinePattern.matchEntire(line)?.let { m ->
                    m.groupValues[1].trim() to m.groupValues[2].trim()
                }
            }
            if (inlinePairs.isNotEmpty() && inlinePairs.size == lines.size) {
                result.addAll(inlinePairs)
                cheatIndex += inlinePairs.size
                continue
            }

            var description: String? = null
            val codes = mutableListOf<String>()
            for (line in lines) {
                if (codePattern.matches(line)) {
                    codes.add(line)
                } else if (description == null) {
                    description = line
                }
            }
            if (codes.isEmpty()) continue

            if (description != null) {
                result.add(description!! to codes.joinToString("\n"))
                cheatIndex++
            } else {
                // No description line: treat each code as a separate cheat.
                for (code in codes) {
                    result.add("Cheat $cheatIndex" to code)
                    cheatIndex++
                }
            }
        }
        return result
    }

    companion object {
        private const val ARG_COLUMN_COUNT = "column-count"
        private const val ARG_GAME_ID = "game_id"
        @JvmStatic
        fun newInstance(gameid: String?, columnCount: Int): LocalCheatItemFragment {
            val fragment = LocalCheatItemFragment()
            val args = Bundle()
            args.putString(ARG_GAME_ID, gameid)
            args.putInt(ARG_COLUMN_COUNT, columnCount)
            fragment.arguments = args
            return fragment
        }

        const val NEW_ITEM = 0
        const val EDIT_ITEM = 1
    }
}
