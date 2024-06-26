using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Spawner : MonoBehaviour
{
    public GameObject[] cubes;
    public float beat = (60 / 130) * 2;
    private float timer;
    private SocketServer socketServer;

    void Start()
    {
        socketServer = gameObject.AddComponent<SocketServer>();
    }

    void Update()
    {
        if (timer > beat)
        {
            if (socketServer.TryGetSpawnPoint(out Vector3 spawnPoint))
            {
                GameObject cube = Instantiate(cubes[Random.Range(0, 2)], spawnPoint, Quaternion.identity);
                cube.transform.localPosition = Vector3.zero;
                cube.transform.position = spawnPoint;
                cube.transform.Rotate(transform.forward, 90 * Random.Range(0, 4));
            }
            timer -= beat;
        }

        timer += Time.deltaTime;
    }
}
