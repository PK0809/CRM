package com.example.calltracker

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class CallUploadService : Service() {

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {

        val phoneNumber = intent?.getStringExtra("phone_number") ?: return START_NOT_STICKY

        sendToServer(phoneNumber)

        return START_NOT_STICKY
    }

    private fun sendToServer(number: String) {

        val json = JSONObject().apply {
            put("phone_number", number)
            put("status", "follow_up")
            put("call_type", "incoming")
            put("duration", 0)
            put("is_completed", false)
        }

        val client = OkHttpClient()

        val body = json.toString()
            .toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("http://192.168.31.7:8000/api/call-log/")
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {

            override fun onFailure(call: okhttp3.Call, e: IOException) {
                Log.e("API_ERROR", e.message ?: "Unknown error")
                stopSelf()
            }

            override fun onResponse(call: okhttp3.Call, response: Response) {
                Log.d("API_RESPONSE", response.code.toString())
                response.close()
                stopSelf()
            }
        })
    }

    override fun onBind(intent: Intent?): IBinder? = null
}