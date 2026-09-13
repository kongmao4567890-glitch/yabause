# 固定 Android APK 签名与覆盖安装

本仓库分发的包名保持 `org.devmiyax.yabasanshioro2.debug`。在线构建使用固定密钥，
`versionCode` 为 `100000 + GitHub Actions 的 run_number`，同一次构建重试保持相同版本号。
后续请保留 `build-apk.yml` 工作流的编号历史；如重建工作流，应提高版本号基数。

## 已安装版本能否覆盖

Android 要求更新包使用原来的签名身份。以前的工作流在临时 runner 上自动生成
`~/.android/debug.keystore`，没有备份或上传该文件。不同构建的签名可能不同。
只有 APK、证书或 SHA-256 指纹无法恢复私钥。

如果保留了原来的 `.jks` / `.keystore`，请导入它。没有原密钥时，新密钥不能直接覆盖
原安装；首次切换需要先导出存档和设置，再卸载旧版并安装固定签名版。后续使用该
固定密钥的构建可以覆盖安装。不要在确认存档已备份前卸载。

参考：[Android 官方签名说明](https://developer.android.com/studio/publish/app-signing)。

## 一次性配置

推荐只配置一个 **Repository secret**：`ANDROID_SIGNING_BUNDLE`，内容为含以下五个
字段的 JSON 对象。所有密钥和密码都留在 GitHub Secrets，不要将 JSON 提交到仓库。
如果已生成 `ANDROID_SIGNING_BUNDLE.txt`，将它的完整内容复制到该 Secret 即可。

配置后在 Actions → Build Android APK → Run workflow 启动构建。
工作流会为 Gradle 注入签名参数，并屏蔽 JSON 内各个字段的日志输出。
配置了 bundle 时优先使用 bundle；格式不完整会报错，不会退回旧签名。

也可以保持原来的五项独立配置：

在仓库 Settings → Secrets and variables → Actions 中配置以下 **Repository secrets**：

| Secret | 内容 |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | 原签名密钥库文件的 Base64 内容（不是 APK） |
| `ANDROID_KEYSTORE_PASSWORD` | 密钥库密码 |
| `ANDROID_KEY_ALIAS` | 签名密钥别名 |
| `ANDROID_KEY_PASSWORD` | 该密钥的密码 |
| `ANDROID_SIGNING_CERT_SHA256` | 签名证书 SHA-256 指纹，允许带冒号 |

在自己的可信电脑上，可用以下命令生成 Base64 内容，并将输出粘贴到对应 Secret：

```sh
python3 -c 'import base64,pathlib; print(base64.b64encode(pathlib.Path("my-signing.keystore").read_bytes()).decode())'
keytool -list -v -keystore my-signing.keystore -alias YOUR_ALIAS
```

第二条命令会提示输入密码，并显示证书的 SHA256 指纹。不要将密钥、密码或 Base64
提交到仓库、Issue 或构建日志。把密钥文件和密码另外保存在私人备份中；不要更换它们。

如果确定原密钥已丢失，可以在可信电脑上生成新的长期密钥（仅执行一次）：

```sh
keytool -genkeypair -keystore my-signing.keystore -storetype PKCS12 \
  -alias yabause -keyalg RSA -keysize 3072 -validity 36500
```

PKCS12 的密钥密码与密钥库密码设为相同。新密钥只能保证今后的版本互相覆盖，
不能解决与旧密钥之间的签名冲突。

配置后在 Actions → Build Android APK → Run workflow 重新编译即可。
未配置完整、证书指纹不匹配或 APK 签名校验失败时会停止，不会退回随机签名。
下载的 APK 压缩包包含 `apk-info.txt`，列出包名、版本号、签名指纹及 APK 校验和。
可以把旧 APK 的 `apksigner verify --print-certs old.apk` 输出与固定指纹对照。

Pull request 只编译检查，不读取签名 Secrets，也不发布可下载的 APK。
本地 IDE 开发仍可使用本地调试签名；需要生成同签名的本地包时，设置
`ANDROID_KEYSTORE_PATH`、`ANDROID_KEYSTORE_PASSWORD`、`ANDROID_KEY_ALIAS`、
`ANDROID_KEY_PASSWORD` 和不低于已安装版本的 `ANDROID_VERSION_CODE`。
