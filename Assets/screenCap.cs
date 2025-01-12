using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class screenCap : MonoBehaviour
{
    public float interval = 1f;
    public string folder = "screenData";
    // Start is called before the first frame update
    void Start()
    {
        StartCoroutine(TakeScreenshots());
    }

    private IEnumerator TakeScreenshots()
    {
        while (true)
        {
            yield return new WaitForSeconds(interval);
            string name = $"{folder}/sc_{System.DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss")}.png";
            ScreenCapture.CaptureScreenshot(name);
            Debug.Log(name);
        }
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}
