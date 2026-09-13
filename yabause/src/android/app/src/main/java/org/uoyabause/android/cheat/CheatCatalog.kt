package org.uoyabause.android.cheat

import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale

data class CatalogCheat(val title: String, val code: String, val raw: String, val reason: String) {
    val importable: Boolean get() = reason.isEmpty() && validCode(code)

    companion object {
        fun codeKey(code: String): String = code.lineSequence().map { it.trim() }
            .filter { it.isNotEmpty() }.joinToString("\n") { it.replace(Regex("\\s+"), " ").uppercase(Locale.ROOT) }

        fun validCode(code: String): Boolean {
            val lines = codeKey(code).lines()
            return lines.isNotEmpty() && lines.all { Regex("[13D][0-9A-F]{7} [0-9A-F]{4}").matches(it) } &&
                !lines.last().startsWith("D")
        }
    }
}

data class CatalogGame(val id: String, val name: String, val source: String,
                       val cheats: List<CatalogCheat>, val notes: String) {
    val availableCount: Int = cheats.count { it.importable }
    private val key = CheatCatalog.normalize(name)
    // Preserve the original searchable title and add established translated series names.
    val searchKey: String = key + " " + key.replace("兰格莉萨", "梦幻模拟战")
        .replace("langrisser", "梦幻模拟战").replace("shiningforce", "光明力量")
}

class CheatCatalog(val games: List<CatalogGame>) {
    fun search(query: String): List<CatalogGame> {
        val key = normalize(query)
        if (key.isEmpty()) return games
        val tokens = query.trim().split(Regex("\\s+")).map(::normalize).filter { it.isNotEmpty() }
        return games.filter { game -> game.searchKey.contains(key) || tokens.all { game.searchKey.contains(it) } }
            .sortedBy { if (normalize(it.name) == key) 0 else if (it.searchKey.startsWith(key)) 1 else 2 }
    }

    companion object {
        fun normalize(value: String): String {
            var text = Normalizer.normalize(value, Normalizer.Form.NFKC).lowercase(Locale.ROOT)
            val roman = mapOf("iii" to "3", "ii" to "2", "iv" to "4", "v" to "5", "vi" to "6")
            text = Regex("(?<![a-z0-9])(iii|ii|iv|vi|v)(?![a-z0-9])").replace(text) { roman[it.value]!! }
            return text.filter { it.isLetterOrDigit() }
        }

        fun fromJson(text: String): CheatCatalog {
            val root = JSONObject(text)
            require(root.getInt("format") == 1)
            val games = root.getJSONArray("games")
            return CheatCatalog((0 until games.length()).map { index ->
                val game = games.getJSONObject(index)
                val entries = game.getJSONArray("entries")
                val notes = game.getJSONArray("notes")
                CatalogGame(game.getString("id"), game.getString("name"), game.getString("source"),
                    (0 until entries.length()).map { i ->
                        val entry = entries.getJSONObject(i)
                        CatalogCheat(entry.getString("title"), entry.getString("code"),
                            entry.getString("raw"), entry.getString("reason"))
                    }, (0 until notes.length()).joinToString("\n\n") { notes.getString(it) })
            })
        }
    }
}
