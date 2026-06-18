package com.miniapp.dto;

public class MiniApiResponse<T> {

    private Integer code;
    private String message;
    private T data;

    public MiniApiResponse() {
    }

    public MiniApiResponse(Integer code, String message, T data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static <T> MiniApiResponse<T> success(T data) {
        return new MiniApiResponse<>(200, "Success", data);
    }

    public static <T> MiniApiResponse<T> fail(Integer code, String message) {
        return new MiniApiResponse<>(code, message, null);
    }

    public Integer getCode() {
        return code;
    }

    public void setCode(Integer code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public T getData() {
        return data;
    }

    public void setData(T data) {
        this.data = data;
    }
}