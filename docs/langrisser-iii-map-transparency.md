# 梦幻模拟战 III：地图突然被实色色块覆盖

两份 T-2502G 存档的 VDP2 显存和调色板完全一致。VDP2 寄存器只有 CCRSA
从 0x0000 变成 0x0A00，即精灵颜色计算比例寄存器 1 变为 10。
异常存档还新增了 21 条地图着色命令：CMDPMOD=0x00A0（256 色 bank），
CMDCOLR=0x5E00，SPCTL=0x1235（精灵类型 5）。

按 [SEGA VDP2 手册 9.1](https://www.infochunk.com/saturn/segahtml_en/hard/vdp2/hon/p09_10.htm)，
类型 5 的位 11 是比例索引，位 12–14 是优先级索引。这些像素应该选择比例 1、
优先级索引 5。PRISC 高字节将索引 5 映射到优先级 2，满足 SPCTL 的颜色计算条件。

OpenGL 的 Vdp1ReadPriority 和 Vulkan 的 readPriority 会先把 CMDCOLR 掩码为
调色板地址。256 色解码随后再次从这个已被掩码的值提取比例，错误地得到 0。
比例 0 在两份存档中均为 0，所以地图着色层被画成不透明，掩盖下方地图细节。

修复在优先级提取前保留原始 bank 寄存器，256 色解码从完整 bank 与像素值中
提取颜色索引和比例。两种后端同步修复，保留已有 RGB 修复和固定签名配置。

## 验证

```sh
python3 yabause/src/tests/test_vdp1_bank_metadata.py
python3 yabause/src/tests/test_vdp1_bank_metadata.py /path/to/T-2502G_*.yss
python3 yabause/src/tests/test_vdp1_rgb_metadata.py
```

测试编译实际 C/C++ 解码函数，并以 UBSan 执行。合成用例覆盖精灵类型 0–7 的
所有优先级/比例组合、调色板地址及零像素透明处理。旧代码首先在类型 0、
CMDCOLR=0x0900 上失败（0xC0000101，应为 0xC8000101）。

用户异常存档中 21 条着色命令共有 14,556 个有效像素；两种后端修复前的元数据
均为 0xC5，修复后均为 0xCD，即正确选择比例 1。正常存档中没有这些着色命令。
原有 RGB、混合 LUT、透明和结束码回归测试也通过。CI 仅运行合成用例，用户存档
不提交到仓库。

验证覆盖实际纹理解码，没有运行完整游戏和地图切换动画，最终画面仍需设备复测。
