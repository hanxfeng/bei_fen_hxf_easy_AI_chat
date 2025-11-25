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

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    // 用于记录当前正在设置哪个头像 ('ai' 或 'user')
    private var currentFileType: String? = null

    // 文件选择请求码
    private val FILE_CHOOSER_REQUEST_CODE = 100

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 1. 找到布局文件中的 WebView (假设 ID 为 myWebView)
        webView = findViewById(R.id.myWebView)

        // 2. 启用 JavaScript 及其他设置
        val webSettings: WebSettings = webView.settings
        webSettings.javaScriptEnabled = true
        webSettings.allowFileAccess = true
        webSettings.allowUniversalAccessFromFileURLs = true
        webSettings.domStorageEnabled = true

        // 3. (可选) 设置 WebViewClient
        webView.webViewClient = WebViewClient()

        // 4. 【关键】添加 JavaScript 桥接
        // 这里的 "AndroidBridge" 必须与 HTML 中 JS 代码调用的 window.AndroidBridge 保持一致
        webView.addJavascriptInterface(AndroidBridge(this, this), AndroidBridge.BRIDGE_NAME)

        // 5. 加载你的本地 HTML 文件
        webView.loadUrl("file:///android_asset/app/index.html")
    }

    // ======================== 文件选择逻辑 ========================

    /**
     * 供 AndroidBridge 调用的方法：启动文件选择
     * 必须在主线程中执行 (由 AndroidBridge 确保)
     * @param fileType 'ai' 或 'user'
     */
    fun startFileSelection(fileType: String) {
        currentFileType = fileType
        val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
            type = "image/*"
        }
        try {
            startActivityForResult(Intent.createChooser(intent, "选择头像图片"), FILE_CHOOSER_REQUEST_CODE)
        } catch (e: Exception) {
            Toast.makeText(this, "无法打开文件选择器: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    /**
     * 处理文件选择的结果
     */
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == FILE_CHOOSER_REQUEST_CODE && resultCode == RESULT_OK) {
            val uri: Uri? = data?.data
            uri?.let {
                // 【关键步骤】将图片 Uri 传回给 JS
                // 使用 Uri.toString() 获取可供 JS 使用的 URI 字符串 (content://...)
                val imageUriString = it.toString()

                // 构建调用 JS 全局函数 setAvatarSrc 的命令
                val jsCommand = "javascript:window.setAvatarSrc('$currentFileType', '$imageUriString');"

                // 在 WebView 中执行 JS 命令
                webView.loadUrl(jsCommand)
            }
        }
    }
}

// ======================== JavaScript 桥接类 ========================

class AndroidBridge(private val context: Context, private val activity: MainActivity) {

    companion object {
        // 必须与 webView.addJavascriptInterface 中的名称保持一致
        const val BRIDGE_NAME = "AndroidBridge"
    }

    /**
     * JS 调用: 保存设置后通知原生端
     */
    @JavascriptInterface
    fun onSettingsSaved(serverUrl: String, serverToken: String) {
        // 【注意】这里是后台线程，如果需要更新 UI 必须使用 runOnUiThread
        activity.runOnUiThread {
            // 示例：显示 Toast 提示
            Toast.makeText(context, "原生端：设置已同步保存！URL: $serverUrl", Toast.LENGTH_SHORT).show()
        }
        // 您可以在这里将 serverUrl 和 serverToken 存储到 SharedPreferences 中
    }

    /**
     * JS 调用: 请求原生端显示 Toast 提示
     */
    @JavascriptInterface
    fun showToast(message: String) {
        // 【注意】这里是后台线程，如果需要更新 UI 必须使用 runOnUiThread
        activity.runOnUiThread {
            Toast.makeText(context, message, Toast.LENGTH_LONG).show()
        }
    }

    /**
     * JS 调用: 请求原生端打开文件选择器
     * @param fileType 'ai' 或 'user'
     */
    @JavascriptInterface
    fun openFileChooser(fileType: String) {
        // 【注意】这里是后台线程，调用 Activity 方法前必须使用 runOnUiThread
        activity.runOnUiThread {
            activity.startFileSelection(fileType) // 调用 Activity 中的方法处理文件选择
        }
    }
}