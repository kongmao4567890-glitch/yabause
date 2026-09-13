# 光明力量 III：魔法后海面透过船体

## 原因和修复

RGB 格式的精灵像素应使用 VDP2 的优先级寄存器 0 和颜色计算比例寄存器 0。
参见 [SEGA VDP2 用户手册 9.2](https://www.infochunk.com/saturn/segahtml_en/hard/vdp2/hon/p09_20.htm)。

OpenGL 和 Vulkan 的 16 位纹理解码把 `CMDCOLR` 中的位当成 RGB 像素的优先级和
混合比例索引。报告中的绘图命令使用 `CMDPMOD=0x142C`（也出现 `0x142E`）、
`CMDCOLR=0x7FFF`，使 RGB 像素错误地选择优先级索引 3、比例索引 7。
在这里 `CMDCOLR` 不应决定 RGB 纹理像素的这些索引。

三份存档均使用 `SPCTL=0x2024`、`CCCTL=0x0442`。前两份的比例寄存器 7 为 0，
第三份变成 24，而比例寄存器 0 仍为 0。因此相同错误在比例为 0 时不明显，
比例被修改后会把原本不透明的 RGB 船体与后面的海面混合。
三份存档不是完整的魔法执行轨迹；它们提供了出错的实际命令和相关寄存器状态。

修复将 RGB16 和混合 LUT 中的 RGB 像素明确编码为索引 `(0, 0)`，避免误读
`CMDCOLR` 或继承前一个调色板像素的比例索引。调色板像素继续使用其原有索引。
OpenGL 和 Vulkan 同步修复，不修改跳帧、限速、滤镜或游戏存档。

## 验证

`test_vdp1_rgb_metadata.py` 提取并编译实际纹理解码函数，使用 UBSan 执行：

```sh
python3 yabause/src/tests/test_vdp1_rgb_metadata.py
# 可选：本地读取实际存档中的 VDP1 命令、纹理和 VDP2 寄存器
python3 yabause/src/tests/test_vdp1_rgb_metadata.py /path/to/*.yss
```

覆盖 RGB16、混合 LUT 的高低半字节、正常调色板索引、透明像素和结束码。
修复前 RGB16 用例输出元数据字节 `0xBB` 而失败，修复后输出正确的 `0x80`。

报告的三份存档中，选中的实际 RGB 纹理像素分别为 13,822、14,333、16,859 个；
两个后端在修复后均通过寄存器索引验证。存档没有上传到源码仓库，CI 只用合成数据。

此验证覆盖实际纹理解码路径，没有在手机上运行完整魔法动画。最终仍需在设备上
读取存档并执行魔法，确认整幅画面恢复正常。APK 构建继续使用固定签名要求；
尚未配置签名 Secrets 时不会发布随机签名包，见 [签名配置](android-signing.md)。
