import React, { useState } from "react"
import { Loader2, Plus, Mic } from "lucide-react"

type ChatState = "input" | "responding" | "with-response"

export default function FloatingChat() {
    const [chatState, setChatState] = useState < ChatState > ("with-response")
    const [message, setMessage] = useState("")
    const [aiResponse, setAiResponse] = useState("Hi there!\nWant me to help?")
    const [isComposing, setIsComposing] = useState(false)

    // Simulate AI response
    const simulateAIResponse = async (userInput: string) => {
        setChatState("responding")
        // Simulate thinking time
        await new Promise((resolve) => setTimeout(resolve, 2000))
        // Set AI response and show it, while showing input again
        setAiResponse(`Thanks for your message: "${userInput}"\nHow else can I help you?`)
        setChatState("with-response")
    }

    const handleSubmit = () => {
        if (!message.trim()) return
        simulateAIResponse(message)
        setMessage("")
    }

    return (
        <div className="min-h-screen bg-transparent flex items-center justify-center p-10">
            {/* 桌宠固定在中心 */}
            <div className="w-50 h-50 flex items-center justify-center relative">
                <div className="w-full h-full rounded-full flex items-center justify-center overflow-hidden">
                    <img
                        src="./assets/pet up-down.gif"
                        alt="Pet animation"
                        className="w-full h-full object-cover"
                    />
                </div>

                {/* Chat bubble - 以桌宠为基准，垂直居中对齐 */}
                {(chatState === "with-response" || chatState === "responding") && (
                    <div className="absolute left-full ml-8 top-1/2 transform -translate-y-1/2">
                        <div className="bg-white rounded-3xl px-6 py-5 max-w-xs shadow-lg">
                            {chatState === "responding" ? (
                                <div className="flex items-center gap-2 text-gray-600">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span className="text-sm">Thinking...</span>
                                </div>
                            ) : (
                                <div className="text-gray-700 text-base leading-relaxed">
                                    {aiResponse.split('\n').map((line, index) => (
                                        <div key={index}>{line}</div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Input bar - 以chat bubble为基准，在正下方 */}
                        {(chatState === "input" || chatState === "with-response") && (
                            <div className="mt-4">
                                <div className="bg-white rounded-full px-6 py-4 flex items-center gap-4 w-96 shadow-lg">
                                    <Plus className="w-5 h-5 text-gray-400" />
                                    <input
                                        type="text"
                                        value={message}
                                        onChange={(e) => setMessage(e.target.value)}
                                        onCompositionStart={() => setIsComposing(true)}
                                        onCompositionEnd={() => setIsComposing(false)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && !isComposing) {
                                                e.preventDefault()
                                                if (message.trim()) {
                                                    handleSubmit()
                                                }
                                            }
                                        }}
                                        placeholder="Describe your task..."
                                        className="flex-1 bg-transparent border-none outline-none text-gray-700 text-base placeholder-gray-400"
                                    />
                                    <button
                                        onClick={handleSubmit}
                                        className="p-0 border-none bg-transparent cursor-pointer"
                                    >
                                        <Mic className="w-5 h-5 text-gray-400 hover:text-gray-600 transition-colors" />
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* 如果只有input状态，单独显示input */}
                {chatState === "input" && (
                    <div className="absolute left-full ml-8 top-1/2 transform -translate-y-1/2">
                        <div className="bg-white rounded-full px-6 py-4 flex items-center gap-4 w-96 shadow-lg">
                            <Plus className="w-5 h-5 text-gray-400" />
                            <input
                                type="text"
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                onCompositionStart={() => setIsComposing(true)}
                                onCompositionEnd={() => setIsComposing(false)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !isComposing) {
                                        e.preventDefault()
                                        if (message.trim()) {
                                            handleSubmit()
                                        }
                                    }
                                }}
                                placeholder="Describe your task..."
                                className="flex-1 bg-transparent border-none outline-none text-gray-700 text-base placeholder-gray-400"
                            />
                            <button
                                onClick={handleSubmit}
                                className="p-0 border-none bg-transparent cursor-pointer"
                            >
                                <Mic className="w-5 h-5 text-gray-400 hover:text-gray-600 transition-colors" />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}