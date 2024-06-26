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
    private Queue<float[]> spawnPoints = new Queue<float[]>();

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

                            if (coords.Length == 5 && float.TryParse(coords[0], out float x) && float.TryParse(coords[1], out float y) && float.TryParse(coords[2], out float z) && float.TryParse(coords[3], out float r) && float.TryParse(coords[4], out float s))
                            {
                                lock (spawnPoints)
                                {
                                    spawnPoints.Enqueue(new float[]{x, y, z, r, s});
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

    public bool GetSpawnPoint(out float[] cube)
    {
        lock (spawnPoints)
        {
            if (spawnPoints.Count > 0)
            {
                cube = spawnPoints.Dequeue();
                return true;
            }
        }
        cube = new float[] {0,0,0,0,0};
        return false;
    }
}