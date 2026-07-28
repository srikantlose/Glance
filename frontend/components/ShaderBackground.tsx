"use client";

import { useEffect, useRef } from "react";

const VERT = `
attribute vec2 a_position;
varying vec2 v_texCoord;
void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
    v_texCoord = a_position * 0.5 + 0.5;
}
`;

const FRAG = `
precision highp float;
varying vec2 v_texCoord;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_mouse;

float grid(vec2 uv, float res) {
    vec2 grid = fract(uv * res);
    return 1.0 - smoothstep(0.0, 0.05, abs(grid.x - 0.5)) * smoothstep(0.0, 0.05, abs(grid.y - 0.5));
}

float pattern(vec2 uv, float t) {
    vec2 p = uv;
    p -= 0.5;
    p.x *= u_resolution.x / u_resolution.y;

    // Rotating geometric lattice
    float angle = t * 0.1;
    mat2 rot = mat2(cos(angle), -sin(angle), sin(angle), cos(angle));
    p = rot * p;

    float d = 0.0;
    for(float i = 0.0; i < 3.0; i++) {
        p = abs(p) - 0.2;
        p = rot * p;
        d += abs(fract(p.x * 2.0 + p.y * 2.0) - 0.5);
    }

    return smoothstep(0.4, 0.5, d);
}

void main() {
    vec2 uv = v_texCoord;
    vec2 mouse = u_mouse / u_resolution;

    float t = u_time * 0.5;

    // Subdued geometric layers
    float g1 = pattern(uv + mouse * 0.05, t);
    float g2 = pattern(uv * 1.5 - mouse * 0.02, t * 0.8);

    // Deep minimalist colors (Obsidian/Slate)
    vec3 color1 = vec3(0.04, 0.05, 0.07); // Deep obsidian
    vec3 color2 = vec3(0.08, 0.09, 0.11); // Dark slate

    vec3 finalColor = mix(color1, color2, g1 * 0.5 + g2 * 0.3);

    // Subtle mouse interaction glow (neutral white/silver)
    float dist = distance(uv, mouse);
    float glow = smoothstep(0.3, 0.0, dist) * 0.02;
    finalColor += glow * vec3(0.8, 0.8, 0.9);

    gl_FragColor = vec4(finalColor, 1.0);
}
`;

export function ShaderBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext("webgl");
    if (!gl) return;

    function resize() {
      if (!canvas || !gl) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      gl.viewport(0, 0, canvas.width, canvas.height);
    }
    resize();
    window.addEventListener("resize", resize);

    const program = gl.createProgram()!;
    const vShader = gl.createShader(gl.VERTEX_SHADER)!;
    gl.shaderSource(vShader, VERT);
    gl.compileShader(vShader);
    gl.attachShader(program, vShader);

    const fShader = gl.createShader(gl.FRAGMENT_SHADER)!;
    gl.shaderSource(fShader, FRAG);
    gl.compileShader(fShader);
    gl.attachShader(program, fShader);

    gl.linkProgram(program);
    gl.useProgram(program);

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);

    const aPosition = gl.getAttribLocation(program, "a_position");
    gl.enableVertexAttribArray(aPosition);
    gl.vertexAttribPointer(aPosition, 2, gl.FLOAT, false, 0, 0);

    const uTime = gl.getUniformLocation(program, "u_time");
    const uResolution = gl.getUniformLocation(program, "u_resolution");
    const uMouse = gl.getUniformLocation(program, "u_mouse");

    let mouseX = 0;
    let mouseY = 0;
    function onMove(e: MouseEvent) {
      mouseX = e.clientX;
      mouseY = window.innerHeight - e.clientY;
    }
    document.addEventListener("mousemove", onMove);

    let frame = 0;
    function render(time: number) {
      if (!gl || !canvas) return;
      gl.uniform1f(uTime, time * 0.001);
      gl.uniform2f(uResolution, canvas.width, canvas.height);
      gl.uniform2f(uMouse, mouseX, mouseY);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      frame = requestAnimationFrame(render);
    }
    frame = requestAnimationFrame(render);

    // client-side nav would otherwise stack a new rAF loop and a new webgl context
    // on every visit to a route that mounts this
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      document.removeEventListener("mousemove", onMove);
      gl.deleteBuffer(buffer);
      gl.deleteShader(vShader);
      gl.deleteShader(fShader);
      gl.deleteProgram(program);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 h-screen w-screen"
    />
  );
}
