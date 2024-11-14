using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

class Program
{
    static void Main()
    {
        Console.WriteLine("Press Ctrl+C to stop the program.");

        while (true)
        {
            // Generate a timestamped filename
            string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string filename = $"screenshot_{timestamp}.png";

            // Set the path to the Desktop
            string desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
            string filepath = Path.Combine(desktopPath, filename);

            // Use screencapture command to take a screenshot on macOS
            var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "screencapture",
                    Arguments = filepath,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                }
            };

            process.Start();
            process.WaitForExit();

            Console.WriteLine($"Screenshot saved to {filepath}");

            // Wait for 10 seconds before taking the next screenshot
            Thread.Sleep(10000); // 10,000 milliseconds = 10 seconds
        }
    }
}
