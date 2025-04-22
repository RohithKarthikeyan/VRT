using System.Collections;
using System.IO;
using System.Net.Sockets;
using UnityEngine;

public class ScreenshotCapture : MonoBehaviour
{
    public float captureInterval = 10.0f; // every 10 seconds
    private string screenshotPath;

    void Start()
    {
        StartCoroutine(CaptureScreenshots());
    }

    IEnumerator CaptureScreenshots()
    {
        while (true)
        {
            yield return new WaitForSeconds(captureInterval);
            yield return StartCoroutine(CaptureAndSendScreenshot());
        }
    }

    IEnumerator CaptureAndSendScreenshot()
    {
        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss");
        string filename = "Screenshot_" + timestamp + ".png";
        screenshotPath = Path.Combine(Application.persistentDataPath, filename);

        ScreenCapture.CaptureScreenshot(screenshotPath);
        Debug.Log("📸 Screenshot saved to: " + screenshotPath);

        // Wait for file to finish writing (important!)
        yield return new WaitUntil(() => File.Exists(screenshotPath));
        yield return new WaitForSeconds(0.5f); // additional delay just in case

        SendScreenshotToServer(screenshotPath);
    }

    void SendScreenshotToServer(string path)
    {
        try
        {
            byte[] imageBytes = File.ReadAllBytes(path);
            TcpClient client = new TcpClient("127.0.0.1", 5001);
            NetworkStream stream = client.GetStream();

            stream.Write(imageBytes, 0, imageBytes.Length);
            stream.Close();
            client.Close();

            Debug.Log($"✅ Sent screenshot ({imageBytes.Length} bytes) to Python server.");
        }
        catch (System.Exception e)
        {
            Debug.LogError("❌ Error sending screenshot: " + e.Message);
        }
    }
}

