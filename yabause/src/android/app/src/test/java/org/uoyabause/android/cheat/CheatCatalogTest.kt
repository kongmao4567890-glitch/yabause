package org.uoyabause.android.cheat

import org.junit.Assert.*
import org.junit.Test
import java.io.File

class CheatCatalogTest {
    private fun catalog(): CheatCatalog {
        val path = listOf("src/main/assets/cheats/catalog.json", "app/src/main/assets/cheats/catalog.json")
            .map(::File).first { it.isFile }
        return CheatCatalog.fromJson(path.readText())
    }

    @Test fun namesIdsVersionsAndAliases() {
        val catalog = catalog()
        assertEquals(759, catalog.games.size)
        assertTrue(catalog.search("光明力量３").any { "GS-9203" in it.name })
        assertTrue(catalog.search("gs 9203").any { "GS-9203" in it.name })
        assertTrue(catalog.search("shining force iii").isNotEmpty())
        assertTrue(catalog.search("梦幻模拟战3").any { "兰格莉萨3" in it.name })
        assertTrue(catalog.search("不存在的游戏abcdef").isEmpty())
        assertEquals(759, catalog.search(" ").size)
        assertTrue(catalog.search("光明力量3").map { it.id }.distinct().size > 3)
    }

    @Test fun completeGroupsOnly() {
        assertTrue(CatalogCheat("条件", "D6000000 0001\n16000002 0002", "", "").importable)
        assertFalse(CatalogCheat("缺行", "D6000000 0001", "", "").importable)
        assertFalse(CatalogCheat("不支持", "16000000 0001\nF6000914 C305", "", "").importable)
        assertFalse(CatalogCheat("缺损", "16000000 0001", "", "incomplete").importable)
        assertEquals("16000000 00FF\n16000002 0001",
            CatalogCheat.codeKey("16000000   00ff\r\n 16000002 0001\n"))
        val all = catalog().games.flatMap { it.cheats }
        assertTrue(all.count { it.importable } > 11000)
        assertTrue(all.any { !it.importable && it.raw.isNotEmpty() })
    }
}
