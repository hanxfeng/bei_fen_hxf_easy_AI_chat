package com.example.bxn

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main) // 关联布局文件

        // 1. 找到布局文件中的 WebView
        val myWebView: WebView = findViewById(R.id.myWebView)

        // 2. 启用 JavaScript (非常重要！否则 JS 无法运行)
        val webSettings: WebSettings = myWebView.settings
        webSettings.javaScriptEnabled = true
        webSettings.allowFileAccess = true
        webSettings.allowUniversalAccessFromFileURLs = true
        webSettings.domStorageEnabled = true
        // 3. (可选) 设置 WebViewClient
        // 这能防止用户点击 HTML 里的链接时，跳转到外部浏览器，而是继续在 App 内打开
        myWebView.webViewClient = WebViewClient()

        // 4. 加载你的本地 HTML 文件
        // "file:///android_asset/" 是访问 assets 文件夹的固定前缀
        // "www/index.html" 是你存放文件的相对路径
        myWebView.loadUrl("file:///android_asset/app/index.html")
    }
}
