using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

public class SocketServer : MonoBehaviour
{
    private Thread socketThread;
    private TcpListener tcpListener;
    private TcpClient connectedTcpClient;
    private bool isRunning = false;
    private Queue<Vector3> spawnPoints = new Queue<Vector3>();

    void Start()
    {
        StartServer();
    }

    void OnApplicationQuit()
    {
        StopServer();
    }

    private void StartServer()
    {
        socketThread = new Thread(() =>
        {
            tcpListener = new TcpListener(IPAddress.Any, 12345);
            tcpListener.Start();
            isRunning = true;

            while (isRunning)
            {
                try
                {
                    using (connectedTcpClient = tcpListener.AcceptTcpClient())
                    using (NetworkStream stream = connectedTcpClient.GetStream())
                    {
                        byte[] bytes = new byte[1024];
                        int length;

                        while ((length = stream.Read(bytes, 0, bytes.Length)) != 0)
                        {
                            var incomingData = new byte[length];
                            Array.Copy(bytes, 0, incomingData, 0, length);
                            string clientMessage = Encoding.ASCII.GetString(incomingData);
                            string[] coords = clientMessage.Split(',');

                            if (coords.Length == 3 && float.TryParse(coords[0], out float x) && float.TryParse(coords[1], out float y) && float.TryParse(coords[2], out float z))
                            {
                                lock (spawnPoints)
                                {
                                    spawnPoints.Enqueue(new Vector3(x, y, z));
                                }
                            }
                        }
                    }
                }
                catch (SocketException socketException)
                {
                    Debug.Log("Socket exception: " + socketException);
                }
            }
        });

        socketThread.IsBackground = true;
        socketThread.Start();
    }

    private void StopServer()
    {
        isRunning = false;
        tcpListener.Stop();
        if (socketThread != null)
        {
            socketThread.Abort();
        }
    }

    public bool TryGetSpawnPoint(out Vector3 spawnPoint)
    {
        lock (spawnPoints)
        {
            if (spawnPoints.Count > 0)
            {
                spawnPoint = spawnPoints.Dequeue();
                return true;
            }
        }
        spawnPoint = Vector3.zero;
        return false;
    }
}