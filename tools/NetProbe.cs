using System;
using System.Net;
class P {
  static void Main() {
    try {
      ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
      using (var wc = new WebClient()) {
        wc.Headers.Add("User-Agent","Phase4Probe");
        Console.WriteLine(wc.DownloadString("https://api.ipify.org"));
      }
    } catch(Exception e) { Console.WriteLine("ERR:"+e.Message); Environment.Exit(2); }
  }
}