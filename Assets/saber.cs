using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

public class saber : MonoBehaviour
{

    public LayerMask layer;
    public LayerMask bombLayer;
    private Vector3 previousPosition;
    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        RaycastHit hit;
        if(Physics.Raycast(transform.position, transform.forward, out hit, 1, layer))
        {
            if (Vector3.Angle(transform.position-previousPosition,hit.transform.up)>130)
            {
                Destroy(hit.transform.gameObject);
            }
        }
        if (Physics.Raycast(transform.position, transform.forward, out hit, 1, bombLayer))
        {
            if (hit.transform.CompareTag("ResetObject")) // Check if the hit object has the specific tag
            {
                ResetGame(); // Call the method to reset the game
            }
        }
        previousPosition = transform.position;
    }
    void ResetGame()
    {
        // Reload the current scene to reset the game
        Scene currentScene = SceneManager.GetActiveScene();
        SceneManager.LoadScene(currentScene.name);
    }
}
