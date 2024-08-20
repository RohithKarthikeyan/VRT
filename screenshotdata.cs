using System.Collections;
using UnityEngine;

public class ScreenshotCapture : MonoBehaviour
{
    public float captureInterval = 60.0f; // Interval in seconds

    void Start()
    {
        // Start the coroutine to capture screenshots
        StartCoroutine(CaptureScreenshots());
    }

    IEnumerator CaptureScreenshots()
    {
        while (true)
        {
            // Wait for the specified interval
            yield return new WaitForSeconds(captureInterval);

            // Capture the screenshot
            CaptureScreenshot();
        }
    }

    void CaptureScreenshot()
    {
        // Define a unique filename
        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss");
        string filename = "Screenshot_" + timestamp + ".png";

        // Capture and save the screenshot
        ScreenCapture.CaptureScreenshot(filename);
        Debug.Log("Screenshot captured: " + filename);

    }

        // If we need to upload stuff to a server add the code for that here 
}
