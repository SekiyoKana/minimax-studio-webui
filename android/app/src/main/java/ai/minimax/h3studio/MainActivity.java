package ai.minimax.h3studio;

import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebChromeClient.FileChooserParams;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String PREFS = "studio_connection";
    private static final String PREF_SERVER = "server_url";
    private static final String PREF_API_KEY = "api_key";
    private static final int STORAGE_PERMISSION_REQUEST = 41;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final ExecutorService networkWorker = Executors.newSingleThreadExecutor();
    private WebView webView;
    private ScrollView connectionPanel;
    private EditText serverAddress;
    private EditText serverApiKey;
    private TextView connectionMessage;
    private Button connectButton;
    private ValueCallback<Uri[]> pendingFileCallback;
    private String serverUrl = "";
    private String pendingDownloadUrl;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.studioWebView);
        connectionPanel = findViewById(R.id.connectionPanel);
        serverAddress = findViewById(R.id.serverAddress);
        serverApiKey = findViewById(R.id.serverApiKey);
        connectionMessage = findViewById(R.id.connectionMessage);
        connectButton = findViewById(R.id.connectButton);
        connectButton.setOnClickListener(view -> connectFromForm());
        setupWebView();

        serverUrl = getSharedPreferences(PREFS, MODE_PRIVATE).getString(PREF_SERVER, "");
        serverApiKey.setText(getSharedPreferences(PREFS, MODE_PRIVATE).getString(PREF_API_KEY, ""));
        if (serverUrl.isEmpty()) {
            showConnectionPanel("");
        } else {
            loadStudio();
        }
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setSupportMultipleWindows(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        CookieManager.getInstance().setAcceptCookie(true);
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidApp");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri target = request.getUrl();
                if (isInternalUrl(target) || "blob".equalsIgnoreCase(target.getScheme())) return false;
                if ("http".equalsIgnoreCase(target.getScheme()) || "https".equalsIgnoreCase(target.getScheme())) {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, target));
                    } catch (ActivityNotFoundException ignored) {
                        Toast.makeText(MainActivity.this, "没有可打开此链接的应用", Toast.LENGTH_SHORT).show();
                    }
                }
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                if (isInternalUrl(Uri.parse(url))) showWebView();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showConnectionPanel("无法连接服务器，请检查地址和网络后重试。" + serverUrl);
                }
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, android.webkit.WebResourceResponse response) {
                if (request.isForMainFrame() && response.getStatusCode() >= 400) {
                    showConnectionPanel("服务器返回错误 " + response.getStatusCode() + "，请检查服务器状态。" + serverUrl);
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> filePathCallback, FileChooserParams params) {
                if (pendingFileCallback != null) pendingFileCallback.onReceiveValue(null);
                pendingFileCallback = filePathCallback;
                Intent intent = params.createIntent();
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, params.getMode() == FileChooserParams.MODE_OPEN_MULTIPLE);
                try {
                    startActivityForResult(intent, FileChooserParams.MODE_OPEN_MULTIPLE + 100);
                } catch (ActivityNotFoundException exception) {
                    pendingFileCallback = null;
                    filePathCallback.onReceiveValue(null);
                    Toast.makeText(MainActivity.this, "没有可用的文件选择器", Toast.LENGTH_SHORT).show();
                }
                return true;
            }
        });

        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> enqueueDownload(url, userAgent, contentDisposition, mimeType));
    }

    private boolean isInternalUrl(Uri uri) {
        if (serverUrl.isEmpty()) return false;
        Uri origin = Uri.parse(serverUrl);
        return equal(origin.getScheme(), uri.getScheme())
                && equal(origin.getHost(), uri.getHost())
                && origin.getPort() == uri.getPort();
    }

    private boolean equal(String left, String right) {
        return left != null && right != null && left.equalsIgnoreCase(right);
    }

    private void connectFromForm() {
        final String candidate;
        try {
            candidate = normalizeServerUrl(serverAddress.getText().toString());
        } catch (IllegalArgumentException exception) {
            connectionMessage.setText(exception.getMessage());
            return;
        }
        connectButton.setEnabled(false);
        connectButton.setText("正在检测…");
        connectionMessage.setText("正在检查服务器连接");
        final String apiKey = serverApiKey.getText().toString().trim();
        networkWorker.execute(() -> {
            String failure = checkServer(candidate, apiKey);
            mainHandler.post(() -> {
                connectButton.setEnabled(true);
                connectButton.setText("检测并连接");
                if (failure != null) {
                    connectionMessage.setText(failure);
                    return;
                }
                serverUrl = candidate;
                getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                        .putString(PREF_SERVER, serverUrl)
                        .putString(PREF_API_KEY, apiKey)
                        .apply();
                applyAuthCookie();
                loadStudio();
            });
        });
    }

    private String normalizeServerUrl(String raw) {
        String value = raw.trim();
        if (value.isEmpty()) throw new IllegalArgumentException("请输入 MiniMax Studio 服务地址");
        if (!value.contains("://")) value = "http://" + value;
        Uri uri = Uri.parse(value);
        String scheme = uri.getScheme();
        if (!("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) || uri.getHost() == null) {
            throw new IllegalArgumentException("地址格式无效，请使用 HTTP 或 HTTPS 地址");
        }
        if (uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null
                || (uri.getPath() != null && !uri.getPath().isEmpty() && !"/".equals(uri.getPath()))) {
            throw new IllegalArgumentException("请只填写服务器域名或 IP 和端口，不要添加路径或参数");
        }
        return scheme.toLowerCase() + "://" + uri.getAuthority();
    }

    private String checkServer(String baseUrl, String apiKey) {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(baseUrl + "/health").openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(4000);
            connection.setReadTimeout(4000);
            connection.setInstanceFollowRedirects(true);
            if (!apiKey.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + apiKey);
            int status = connection.getResponseCode();
            if (status != HttpURLConnection.HTTP_OK) return "服务器检测失败，HTTP " + status;
            StringBuilder body = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) body.append(line);
            }
            if (!"ok".equalsIgnoreCase(new JSONObject(body.toString()).optString("status"))) {
                return "该地址没有返回 MiniMax Studio 健康状态";
            }
            return null;
        } catch (Exception exception) {
            return "连接失败，请确认 MiniMax Studio 已启动且地址可访问。";
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private void loadStudio() {
        applyAuthCookie();
        showWebView();
        webView.loadUrl(serverUrl + "/?h3_client=android");
    }

    private void applyAuthCookie() {
        if (serverUrl.isEmpty()) return;
        String apiKey = getSharedPreferences(PREFS, MODE_PRIVATE).getString(PREF_API_KEY, "");
        String cookie = apiKey.isEmpty()
                ? "h3_api_key=; Max-Age=0; Path=/"
                : "h3_api_key=" + apiKey + "; Path=/";
        CookieManager.getInstance().setCookie(serverUrl, cookie);
        CookieManager.getInstance().flush();
    }

    private void showWebView() {
        connectionPanel.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
    }

    private void showConnectionPanel(String message) {
        serverAddress.setText(serverUrl);
        serverApiKey.setText(getSharedPreferences(PREFS, MODE_PRIVATE).getString(PREF_API_KEY, ""));
        connectionMessage.setText(message);
        webView.setVisibility(View.GONE);
        connectionPanel.setVisibility(View.VISIBLE);
    }

    private void enqueueDownload(String url, String userAgent, String contentDisposition, String mimeType) {
        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P
                && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            pendingDownloadUrl = url;
            requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, STORAGE_PERMISSION_REQUEST);
            return;
        }
        DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
        String cookie = CookieManager.getInstance().getCookie(url);
        if (cookie != null) request.addRequestHeader("Cookie", cookie);
        if (userAgent != null) request.addRequestHeader("User-Agent", userAgent);
        if (mimeType != null) request.setMimeType(mimeType);
        request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
        request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, URLUtil.guessFileName(url, contentDisposition, mimeType));
        DownloadManager manager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
        manager.enqueue(request);
        Toast.makeText(this, "已加入下载", Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != FileChooserParams.MODE_OPEN_MULTIPLE + 100 || pendingFileCallback == null) return;
        Uri[] results = null;
        if (resultCode == RESULT_OK && data != null) {
            if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount();
                results = new Uri[count];
                for (int index = 0; index < count; index++) results[index] = data.getClipData().getItemAt(index).getUri();
            } else if (data.getData() != null) {
                results = new Uri[]{data.getData()};
            }
        }
        pendingFileCallback.onReceiveValue(results);
        pendingFileCallback = null;
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != STORAGE_PERMISSION_REQUEST) return;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED && pendingDownloadUrl != null) {
            String url = pendingDownloadUrl;
            pendingDownloadUrl = null;
            enqueueDownload(url, webView.getSettings().getUserAgentString(), null, null);
        } else {
            pendingDownloadUrl = null;
            Toast.makeText(this, "未获得下载权限", Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        if (webView.getVisibility() == View.VISIBLE && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (pendingFileCallback != null) pendingFileCallback.onReceiveValue(null);
        networkWorker.shutdownNow();
        webView.destroy();
        super.onDestroy();
    }

    private final class AndroidBridge {
        @JavascriptInterface
        public void openServerSettings() {
            runOnUiThread(() -> showConnectionPanel(""));
        }
    }
}
