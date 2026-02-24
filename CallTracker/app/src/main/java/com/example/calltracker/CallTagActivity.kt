package com.example.calltracker

import android.os.Bundle
import android.util.Log
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class CallTagActivity : AppCompatActivity() {

    private lateinit var phoneNumber: String
    private lateinit var etName: EditText
    private lateinit var etAddress: EditText
    private lateinit var etRemarks: EditText
    private lateinit var spinner: Spinner
    private lateinit var statusMap: Map<String, String>

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_call_tag)

        phoneNumber = intent.getStringExtra("phone_number") ?: "Unknown"

        val tvPhoneNumber = findViewById<TextView>(R.id.tvPhoneNumber)
        etName = findViewById(R.id.etName)
        etAddress = findViewById(R.id.etAddress)
        etRemarks = findViewById(R.id.etRemarks)
        spinner = findViewById(R.id.spStatus)
        val btnSave = findViewById<Button>(R.id.btnSave)

        tvPhoneNumber.text =
            getString(R.string.phone_number_label, phoneNumber)

        // UI → Backend mapping
        statusMap = mapOf(
            getString(R.string.status_follow_up) to "follow_up",
            getString(R.string.status_junk) to "junk",
            getString(R.string.status_lead_stage) to "lead_stage",
            getString(R.string.status_existing_client) to "existing_client"
        )

        spinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            statusMap.keys.toList()
        )

        btnSave.setOnClickListener {

            val selectedDisplay = spinner.selectedItem.toString()
            val actualStatus = statusMap[selectedDisplay] ?: "follow_up"

            val json = JSONObject().apply {
                put("phone_number", phoneNumber)
                put("name", etName.text.toString())
                put("address", etAddress.text.toString())
                put("remarks", etRemarks.text.toString())
                put("status", actualStatus)

                // 🔥 VERY IMPORTANT
                put("is_completed", true)
            }

            sendUpdate(json)
        }
    }

    // ==========================
    // UPDATE RECORD
    // ==========================
    private fun sendUpdate(json: JSONObject) {

        Log.d("FORM_JSON", json.toString())

        val client = OkHttpClient()

        val requestBody = json.toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url("http://crm.isecuresolutions.in/api/call-log/")
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {

            override fun onFailure(call: Call, e: IOException) {
                Log.e("API_ERROR", e.message ?: "Unknown error")
            }

            override fun onResponse(call: Call, response: Response) {

                Log.d("FORM_RESPONSE", response.code.toString())

                val success = response.isSuccessful
                response.close()

                if (success) {
                    runOnUiThread {
                        Toast.makeText(
                            this@CallTagActivity,
                            getString(R.string.saved_success),
                            Toast.LENGTH_SHORT
                        ).show()
                        finish()
                    }
                }
            }
        })
    }
}