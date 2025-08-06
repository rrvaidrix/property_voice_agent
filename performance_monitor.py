#!/usr/bin/env python3
"""
Performance Monitor for Voice Assistant API
Tracks response times and helps identify bottlenecks
"""

import time
import requests
import json
import statistics
from datetime import datetime

class PerformanceMonitor:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.response_times = {
            'health': [],
            'start_conversation': [],
            'process_user_input': []
        }
    
    def test_health_endpoint(self, iterations=5):
        """Test health endpoint response time"""
        print("🏥 Testing health endpoint...")
        times = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}/health", timeout=10)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                times.append(response_time)
                print(f"  Health check {i+1}: {response_time:.2f}ms")
            except Exception as e:
                print(f"  Health check {i+1}: ERROR - {e}")
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            print(f"  📊 Health endpoint - Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
            self.response_times['health'].extend(times)
    
    def test_start_conversation(self, iterations=3):
        """Test start conversation endpoint response time"""
        print("🎤 Testing start conversation endpoint...")
        times = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                response = requests.post(
                    f"{self.base_url}/api/start_conversation",
                    json={"language": "English"},
                    timeout=30
                )
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                times.append(response_time)
                print(f"  Start conversation {i+1}: {response_time:.2f}ms")
            except Exception as e:
                print(f"  Start conversation {i+1}: ERROR - {e}")
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            print(f"  📊 Start conversation - Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
            self.response_times['start_conversation'].extend(times)
    
    def generate_test_audio(self, duration_seconds=3):
        """Generate a simple test audio file for testing"""
        import numpy as np
        import wave
        
        # Generate a simple sine wave
        sample_rate = 16000
        frequency = 440  # A4 note
        samples = int(sample_rate * duration_seconds)
        t = np.linspace(0, duration_seconds, samples)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # Convert to 16-bit PCM
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Save as WAV file
        with wave.open('test_audio.wav', 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        return 'test_audio.wav'
    
    def test_process_user_input(self, iterations=3):
        """Test process user input endpoint response time"""
        print("🎵 Testing process user input endpoint...")
        times = []
        
        # Generate test audio
        test_audio_file = self.generate_test_audio(2)
        
        for i in range(iterations):
            start_time = time.time()
            try:
                with open(test_audio_file, 'rb') as audio_file:
                    files = {'audio': ('test.wav', audio_file, 'audio/wav')}
                    data = {'language': 'English'}
                    
                    response = requests.post(
                        f"{self.base_url}/api/process_user_input",
                        files=files,
                        data=data,
                        timeout=60
                    )
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                times.append(response_time)
                print(f"  Process user input {i+1}: {response_time:.2f}ms")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'success':
                        print(f"    ✅ Success - User: '{result.get('user_input', 'N/A')[:50]}...'")
                    else:
                        print(f"    ❌ Error: {result.get('message', 'Unknown error')}")
                else:
                    print(f"    ❌ HTTP Error: {response.status_code}")
                    
            except Exception as e:
                print(f"  Process user input {i+1}: ERROR - {e}")
        
        # Clean up test file
        import os
        if os.path.exists(test_audio_file):
            os.remove(test_audio_file)
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            print(f"  📊 Process user input - Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
            self.response_times['process_user_input'].extend(times)
    
    def run_full_test(self):
        """Run complete performance test suite"""
        print("=" * 60)
        print("🚀 Voice Assistant API Performance Test")
        print("=" * 60)
        print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Target API: {self.base_url}")
        print("=" * 60)
        
        # Test all endpoints
        self.test_health_endpoint(5)
        print()
        self.test_start_conversation(3)
        print()
        self.test_process_user_input(3)
        print()
        
        # Summary
        print("=" * 60)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        for endpoint, times in self.response_times.items():
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                print(f"🎯 {endpoint.replace('_', ' ').title()}:")
                print(f"   Average: {avg_time:.2f}ms")
                print(f"   Range: {min_time:.2f}ms - {max_time:.2f}ms")
                print()
        
        print("=" * 60)
        print("✅ Performance test completed!")
        print("💡 Tips for further optimization:")
        print("   • Check network latency to API providers")
        print("   • Monitor server CPU and memory usage")
        print("   • Consider using faster models if available")
        print("   • Optimize audio file size and format")
        print("=" * 60)

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    monitor.run_full_test() 