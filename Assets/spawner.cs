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
    //if (timer > beat)
    //{
        if (socketServer.GetSpawnPoint(out float[] spawn))
        {
            Vector3 spawnPoint = new Vector3(spawn[0], spawn[1], spawn[2]);
            GameObject cube = Instantiate(cubes[Random.Range(0, 2)], spawnPoint, Quaternion.identity);
            cube.transform.localPosition = Vector3.zero;
            cube.transform.position = spawnPoint;
            cube.transform.Rotate(transform.forward, spawn[3]);
            CubeMove cubeMove = cube.GetComponent<CubeMove>();
            cubeMove.SetSpeed(spawn[4]);
        }
    //    timer -= beat;
    //}

    //    timer += Time.deltaTime;
    }
}
