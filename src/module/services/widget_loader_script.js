(function() {
const currentScript = document.currentScript.src;
    const urlParams = new URLSearchParams(currentScript.split("?")[1]);
    const widgetId = urlParams.get("id");

    if (!widgetId) {
        return console.error("Widget ID missing from script tag.");
    }

    fetch(`${process.env.BASE_URL}/v1/widgets/` + widgetId + `/config`)
        .then(response => {
            if (!response.ok) {
                return response.text().then(errorText => {
                throw new Error(`Config endpoint returned ${response.status}. Info: ${errorText}`);
            })}
            return response.json();
        })
        .then(config => {
            if (!config.id || !config.settings) {
                return console.error("Invalid widget configuration schema.");
            }

            const settings = config.settings;
            // Build Container DOM
            const container = document.createElement("div");
            container.id = "widget-" + widgetId;
            container.style.cssText = "position:fixed;bottom:20px;right:20px;z-index:9999;background:#fff;padding:20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-family:sans-serif;max-width:350px;";

            const titleElement = document.createElement("h3");
            titleElement.textContent = config.title || "Widget";
            titleElement.style.margin = "0 0 15px 0";
            container.appendChild(titleElement);

            // Construct Form Body
            const form = document.createElement("form");
            form.id = "widget-form-" + widgetId;

            // Render Dynamic Fields
            if (Array.isArray(settings.fields)) {
                settings.fields.forEach(field => {
                    const fieldWrapper = document.createElement("div");
                    fieldWrapper.style.marginBottom = "10px";

                    const label = document.createElement("label");
                    label.textContent = field.label;
                    label.style.cssText = "display:block;margin-bottom:5px;font-size:12px;font-weight:bold;";

                    const input = document.createElement(field.type === "textarea" ? "textarea" : "input");
                    if (field.type !== "textarea") input.type = field.type;
                    input.name = field.name;
                    input.required = !!field.required;
                    input.style.cssText = "width:100%;padding:8px;box-sizing:border-box;border:1px solid #ccc;border-radius:4px;";

                    fieldWrapper.appendChild(label);
                    fieldWrapper.appendChild(input);
                    form.appendChild(fieldWrapper);
                });
            }

            // Inject Honeypot Anti-Spam Control Field
            const honeypot = document.createElement("input");
            honeypot.type = "text";
            honeypot.name = "_hp_confirm";
            honeypot.style.display = "none";
            honeypot.tabIndex = -1;
            honeypot.autocomplete = "off";
            form.appendChild(honeypot);

            // Submit Button
            const submitBtn = document.createElement("button");
            submitBtn.type = "submit";
            submitBtn.textContent = settings.submit_button_text || "Submit";
            submitBtn.style.cssText = "background:#007bff;color:#fff;padding:10px;border:none;border-radius:4px;cursor:pointer;width:100%;font-weight:bold;";
            form.appendChild(submitBtn);

            container.appendChild(form);
            document.body.appendChild(container);

            // Submission Handler Enforcing Schema Structural Compliance
            form.addEventListener("submit", function(event) {
                event.preventDefault();

                const rawFormData = new FormData(form);
                const formDataMap = {};
                let hpValue = "";

                rawFormData.forEach((value, key) => {
                    if (key === "_hp_confirm") {
                        hpValue = value.toString();
                    } else {
                        formDataMap[key] = value.toString();
                    }
                });

                // Match Payload Specification
                const ingestionPayload = {
                    widget_id: widgetId,
                    form_data: formDataMap,
                    _hp_confirm: hpValue
                };

                fetch(`${process.env.BASE_URL}/v1/submissions`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(ingestionPayload)
                })
                .then(res => {
                    if (!res.ok) throw new Error("Submission failed with status " + res.status);
                    return res.json();
                })
                .then(() => {
                    alert(settings.success_message || "Form submitted successfully!");
                    form.reset();
                })
                .catch(err => console.error("Submission pipeline error:", err));
            });
        })
        .catch(err => console.error("Widget initialization failed:", err));
})();