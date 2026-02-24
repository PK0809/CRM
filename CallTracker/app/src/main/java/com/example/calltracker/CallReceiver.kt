package com.example.calltracker

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.database.Cursor
import android.os.Handler
import android.os.Looper
import android.provider.CallLog
import android.telephony.TelephonyManager
import android.util.Log
import androidx.core.app.NotificationCompat
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class CallReceiver : BroadcastReceiver() {

    companion object {
        private var lastProcessedCallTime: Long = 0
    }

    override fun onReceive(context: Context, intent: Intent) {

        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return

        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)

        if (state == TelephonyManager.EXTRA_STATE_IDLE) {

            Handler(Looper.getMainLooper()).postDelayed({

                val cursor: Cursor? = context.contentResolver.query(
                    CallLog.Calls.CONTENT_URI,
                    null,
                    null,
                    null,
                    "${CallLog.Calls.DATE} DESC"
                )

                cursor?.use { c ->

                    if (!c.moveToFirst()) return@use

                    val numberIndex = c.getColumnIndex(CallLog.Calls.NUMBER)
                    val durationIndex = c.getColumnIndex(CallLog.Calls.DURATION)
                    val dateIndex = c.getColumnIndex(CallLog.Calls.DATE)
                    val simIndex = c.getColumnIndex(CallLog.Calls.PHONE_ACCOUNT_ID)

                    if (numberIndex < 0 || durationIndex < 0 || dateIndex < 0) return@use

                    val number = c.getString(numberIndex)
                    val duration = c.getLong(durationIndex)
                    val callTime = c.getLong(dateIndex)

                    // Prevent duplicate processing
                    if (callTime == lastProcessedCallTime) return@use
                    lastProcessedCallTime = callTime

                    // SIM Detection (device-specific mapping)
                    val simInfo: String

                    if (simIndex >= 0) {
                        val accountId = c.getString(simIndex)
                        Log.d("SIM_DEBUG", "PHONE_ACCOUNT_ID: $accountId")

                        simInfo = "SIM $accountId"
                    } else {
                        simInfo = "UNKNOWN"
                    }

                    Log.d("CALL_DEBUG", "Number: $number | Duration: $duration | SIM: $simInfo")

                    if (duration == 0L) {
                        // Missed Call → Auto Save Only
                        autoSave(number, 0L, "missed", simInfo)
                    } else {
                        // Picked Call → Auto Save + Notification
                        autoSave(number, duration, "incoming", simInfo)
                        showCallNotification(context, number, duration)
                    }
                }

            }, 1500)
        }
    }

    // ==========================
    // AUTO SAVE TO DJANGO
    // ==========================
    private fun autoSave(
        number: String,
        duration: Long,
        callType: String,
        simInfo: String
    ) {

        val json = JSONObject().apply {
            put("phone_number", number)
            put("status", if (callType == "missed") "missed" else "follow_up")
            put("call_type", callType)
            put("duration", duration)
            put("sim_slot", simInfo)
            put("is_completed", false)
        }

        val client = OkHttpClient()

        val body = json.toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url("http://192.168.31.7:8000/api/call-log/")
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {

            override fun onFailure(call: Call, e: IOException) {
                Log.e("API_ERROR", e.message ?: "Unknown error")
            }

            override fun onResponse(call: Call, response: Response) {
                Log.d("API_RESPONSE", response.code.toString())
                response.close()
            }
        })
    }

    // ==========================
    // SHOW NOTIFICATION
    // ==========================
    private fun showCallNotification(
        context: Context,
        number: String,
        duration: Long
    ) {

        val channelId = "call_channel"

        val manager =
            context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val channel = NotificationChannel(
            channelId,
            "Call Tagging",
            NotificationManager.IMPORTANCE_HIGH
        )
        manager.createNotificationChannel(channel)

        val intent = Intent(context, CallTagActivity::class.java).apply {
            putExtra("phone_number", number)
            putExtra("duration", duration)
            putExtra("call_type", "incoming")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            number.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.sym_call_incoming)
            .setContentTitle("Call Ended")
            .setContentText("Tap to add call details")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        manager.notify(number.hashCode(), notification)
    }
}