package com.example.bxn

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.edit
import java.io.File
import java.io.FileOutputStream

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var currentFileType: String? = null
    private val FILE_CHOOSER_REQUEST_CODE = 100

    // SharedPreferences 的常量
    companion object {
        const val PREFS_NAME = "PA4_Chat_Prefs"
        const val KEY_SERVER_URL = "serverUrl"
        const val KEY_SERVER_TOKEN = "serverToken"
        const val KEY_AI_AVATAR = "aiAvatarPath"
        const val KEY_USER_AVATAR = "userAvatarPath"
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.myWebView)

        // 1. WebView 设置 (保持不变)
        val webSettings: WebSettings = webView.settings
        webSettings.javaScriptEnabled = true
        webSettings.allowFileAccess = true
        webSettings.allowUniversalAccessFromFileURLs = true
        webSettings.domStorageEnabled = true // 虽然我们不用它存设置，但 JS 其他地方可能用

        // 2. 添加桥接
        webView.addJavascriptInterface(AndroidBridge(this, this), AndroidBridge.BRIDGE_NAME)

        // 3. 【关键修改】设置 WebViewClient 以便在页面加载后注入设置
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                // 页面加载完成后，从 SharedPreferences 读取设置并注入 JS
                injectSettingsIntoJs()
            }
        }

        // 4. 加载 HTML
        webView.loadUrl("file:///android_asset/app/index.html")
    }

    /**
     * 【新增】从 SharedPreferences 读取设置并调用 JS 的初始化函数
     */
    private fun injectSettingsIntoJs() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val serverUrl = prefs.getString(KEY_SERVER_URL, "") ?: ""
        val serverToken = prefs.getString(KEY_SERVER_TOKEN, "") ?: ""
        val aiAvatarPath = prefs.getString(KEY_AI_AVATAR, "") ?: ""
        val userAvatarPath = prefs.getString(KEY_USER_AVATAR, "") ?: ""

        // 构建一个 JSON 对象字符串
        val configJson = """
            {
                "serverUrl": "$serverUrl",
                "token": "$serverToken",
                "aiAvatarPath": "$aiAvatarPath",
                "userAvatarPath": "$userAvatarPath"
            }
        """.trimIndent()

        // 调用 JS 中的全局函数 window.initializeSettings
        // 使用 runOnUiThread 确保在 UI 线程执行
        runOnUiThread {
            webView.loadUrl("javascript:window.initializeSettings($configJson);")
        }
    }

    /**
     * 【新增】将选择的头像(Uri)复制到应用内部存储，并返回永久路径
     */
    private fun saveAvatarToFile(uri: Uri, fileType: String): String? {
        try {
            val fileName = if (fileType == "ai") "ai_avatar.png" else "user_avatar.png"
            val destinationFile = File(filesDir, fileName)

            // 使用 ContentResolver 来读取 Uri 的输入流
            val inputStream = contentResolver.openInputStream(uri) ?: return null
            // 创建到应用内部文件的输出流
            val outputStream = FileOutputStream(destinationFile)

            // 复制文件
            inputStream.use { input ->
                outputStream.use { output ->
                    input.copyTo(output)
                }
            }

            // 返回这个文件的永久 URI 路径 (e.g., file:///data/data/com.example.bxn/files/ai_avatar.png)
            return destinationFile.toURI().toString()

        } catch (e: Exception) {
            e.printStackTrace()
            runOnUiThread {
                Toast.makeText(this, "保存头像失败: ${e.message}", Toast.LENGTH_LONG).show()
            }
            return null
        }
    }

    // ======================== 文件选择逻辑 (修改) ========================

    fun startFileSelection(fileType: String) {
        currentFileType = fileType
        val intent = Intent(Intent.ACTION_GET_CONTENT).apply { type = "image/*" }
        try {
            startActivityForResult(Intent.createChooser(intent, "选择头像图片"), FILE_CHOOSER_REQUEST_CODE)
        } catch (e: Exception) {
            Toast.makeText(this, "无法打开文件选择器: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == FILE_CHOOSER_REQUEST_CODE && resultCode == RESULT_OK) {
            val uri: Uri? = data?.data
            val fileType = currentFileType ?: return

            uri?.let {
                // 【关键修改】复制文件到内部存储
                val permanentPath = saveAvatarToFile(it, fileType)

                if (permanentPath != null) {
                    // 1. 将永久路径保存到 SharedPreferences
                    val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                    prefs.edit {
                        if (fileType == "ai") {
                            putString(KEY_AI_AVATAR, permanentPath)
                        } else {
                            putString(KEY_USER_AVATAR, permanentPath)
                        }
                    }

                    // 2. 将永久路径回传给 JS
                    val jsCommand = "javascript:window.setAvatarSrc('$fileType', '$permanentPath');"
                    webView.loadUrl(jsCommand)
                }
            }
        }
    }
}

// ======================== JavaScript 桥接类 (修改) ========================

class AndroidBridge(private val context: Context, private val activity: MainActivity) {

    companion object {
        const val BRIDGE_NAME = "AndroidBridge"
    }

    /**
     * JS 调用: 保存设置后通知原生端
     * 【修改】: 现在保存到 SharedPreferences
     */
    @JavascriptInterface
    fun onSettingsSaved(serverUrl: String, serverToken: String) {
        val prefs = context.getSharedPreferences(MainActivity.PREFS_NAME, Context.MODE_PRIVATE)

        // 使用 KTX 扩展函数简化编辑
        prefs.edit {
            putString(MainActivity.KEY_SERVER_URL, serverUrl)
            putString(MainActivity.KEY_SERVER_TOKEN, serverToken)
        }

        activity.runOnUiThread {
            Toast.makeText(context, "原生端：设置已保存！", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * JS 调用: 请求原生端显示 Toast 提示 (保持不变)
     */
    @JavascriptInterface
    fun showToast(message: String) {
        activity.runOnUiThread {
            Toast.makeText(context, message, Toast.LENGTH_LONG).show()
        }
    }

    /**
     * JS 调用: 请求原生端打开文件选择器 (保持不变)
     */
    @JavascriptInterface
    fun openFileChooser(fileType: String) {
        activity.runOnUiThread {
            activity.startFileSelection(fileType)
        }
    }
}