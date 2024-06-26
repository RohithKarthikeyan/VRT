using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class CubeMove : MonoBehaviour
{
    // Start is called before the first frame update
    //private SocketServer socketServer;
    private float speed = 1;
    void Start()
    {
        //socketServer = gameObject.AddComponent<SocketServer>();
    }

    // Update is called once per frame
    void Update()
    {
        //if (socketServer.getSpeed(out float speed))
        //{
            transform.position += Time.deltaTime * transform.forward * speed;
        //}
        if(transform.position.z > 1)
        {
            Destroy(gameObject);
        }
    }
    public void SetSpeed(float newSpeed)
    {
        speed = newSpeed;
    }
}
