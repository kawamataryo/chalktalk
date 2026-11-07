import CoreGraphics
import Foundation
import SwiftUI

/// SVG のパス（`d` の文字列）を読んで `Path` にする（#173）。自由に描く黒板の `path` 図形で使う。
///
/// コマンド M/L/H/V/C/S/Q/T/A/Z（大文字は絶対、小文字は相対）と、同じコマンドの繰り返しの省略に対応する。
/// 知らない文字や数の足りないコマンドが来たら、そこで読むのをやめて、それまでの線を返す（図ごと捨てない）。
/// 座標は黒板の外に大きくはみ出さないように収める。
enum SVGPathParser {
    /// 1 本のパスの長さの上限（モデルが長いパスを書いても、描くのが重くならないように）
    static let maxCommands = 400

    static func path(from d: String, clampTo bounds: CGRect = CGRect(x: -10, y: -10, width: ChalkDrawing.width + 20, height: ChalkDrawing.height + 20)) -> Path {
        var scanner = Tokenizer(d)
        var path = Path()
        var current = CGPoint.zero
        var subpathStart = CGPoint.zero
        /// 前のコマンドの制御点（S・T で反転して使う）
        var lastCubicControl: CGPoint?
        var lastQuadControl: CGPoint?
        var command: Character?
        var hasMove = false
        var count = 0

        func clamp(_ p: CGPoint) -> CGPoint {
            CGPoint(x: min(max(p.x, bounds.minX), bounds.maxX), y: min(max(p.y, bounds.minY), bounds.maxY))
        }

        while count < maxCommands {
            scanner.skipSeparators()
            if scanner.isAtEnd { break }
            if let letter = scanner.letter() {
                guard "MmLlHhVvCcSsQqTtAaZz".contains(letter) else { break }
                command = letter
            } else if command == nil {
                break
            }
            guard let cmd = command else { break }
            let relative = cmd.isLowercase
            let base = relative ? current : .zero
            func point(_ x: Double, _ y: Double) -> CGPoint { CGPoint(x: base.x + x, y: base.y + y) }
            count += 1

            switch cmd.uppercased() {
            case "M":
                guard let x = scanner.number(), let y = scanner.number() else { return path }
                current = clamp(point(x, y))
                path.move(to: current)
                subpathStart = current
                hasMove = true
                // M のあとに続く座標は L として読む
                command = relative ? "l" : "L"
                lastCubicControl = nil; lastQuadControl = nil
            case "L":
                guard let x = scanner.number(), let y = scanner.number() else { return path }
                if !hasMove { path.move(to: current); hasMove = true }
                current = clamp(point(x, y))
                path.addLine(to: current)
                lastCubicControl = nil; lastQuadControl = nil
            case "H":
                guard let x = scanner.number() else { return path }
                if !hasMove { path.move(to: current); hasMove = true }
                current = clamp(CGPoint(x: (relative ? current.x : 0) + x, y: current.y))
                path.addLine(to: current)
                lastCubicControl = nil; lastQuadControl = nil
            case "V":
                guard let y = scanner.number() else { return path }
                if !hasMove { path.move(to: current); hasMove = true }
                current = clamp(CGPoint(x: current.x, y: (relative ? current.y : 0) + y))
                path.addLine(to: current)
                lastCubicControl = nil; lastQuadControl = nil
            case "C":
                guard let x1 = scanner.number(), let y1 = scanner.number(), let x2 = scanner.number(), let y2 = scanner.number(),
                      let x = scanner.number(), let y = scanner.number() else { return path }
                if !hasMove { path.move(to: current); hasMove = true }
                let c1 = clamp(point(x1, y1)), c2 = clamp(point(x2, y2))
                current = clamp(point(x, y))
                path.addCurve(to: current, control1: c1, control2: c2)
                lastCubicControl = c2; lastQuadControl = nil
            case "S":
                guard let x2 = scanner.number(), let y2 = scanner.number(), let x = scanner.number(), let y = scanner.number() else { return path }
                if !hasMove { path.move(to: current); hasMove = true }
                let c1 = lastCubicControl.map { CGPoint(x: 2 * current.x - $0.x, y: 2 * current.y - $0.y) } ?? current
                let c2 = clamp(point(x2, y2))
                current = clamp(point(x, y))
                path.addCurve(to: current, control1: c1, control2: c2)
                lastCubicControl = c2; lastQuadControl = nil
            case "Q":
                guard let x1 = scanner.number(), let y1 = scanner.number(), let x = scanner.number(), let y = scanner.number() else { return path }
                if !hasMove { path.move(to: current); hasMove = true }
                let c = clamp(point(x1, y1))
                current = clamp(point(x, y))
                path.addQuadCurve(to: current, control: c)
                lastQuadControl = c; lastCubicControl = nil
            case "T":
                guard let x = scanner.number(), let y = scanner.number() else { return path }
                if !hasMove { path.move(to: current); hasMove = true }
                let c = lastQuadControl.map { CGPoint(x: 2 * current.x - $0.x, y: 2 * current.y - $0.y) } ?? current
                current = clamp(point(x, y))
                path.addQuadCurve(to: current, control: c)
                lastQuadControl = c; lastCubicControl = nil
            case "A":
                guard let rx = scanner.number(), let ry = scanner.number(), let rotation = scanner.number(),
                      let large = scanner.flag(), let sweep = scanner.flag(),
                      let x = scanner.number(), let y = scanner.number() else { return path }
                if !hasMove { path.move(to: current); hasMove = true }
                let end = clamp(point(x, y))
                addArc(to: &path, from: current, to: end, rx: rx, ry: ry, rotation: rotation, largeArc: large, sweep: sweep)
                current = end
                lastCubicControl = nil; lastQuadControl = nil
            case "Z":
                if hasMove { path.closeSubpath() }
                current = subpathStart
                lastCubicControl = nil; lastQuadControl = nil
                // Z のあとは数が続かない。次はコマンドの文字が来るはず
                command = nil
            default:
                return path
            }
        }
        return path
    }

    /// 弧（SVG の書き方）を 3 次ベジェ曲線で足す（SVG 1.1 付録 F.6 の中心の求め方）
    static func addArc(to path: inout Path, from p0: CGPoint, to p1: CGPoint, rx rxIn: Double, ry ryIn: Double,
                       rotation: Double, largeArc: Bool, sweep: Bool) {
        var rx = abs(rxIn), ry = abs(ryIn)
        guard p0 != p1 else { return }
        guard rx > 0, ry > 0 else { path.addLine(to: p1); return }
        let phi = rotation * .pi / 180
        let cosPhi = cos(phi), sinPhi = sin(phi)
        let dx = (p0.x - p1.x) / 2, dy = (p0.y - p1.y) / 2
        let x1p = cosPhi * dx + sinPhi * dy
        let y1p = -sinPhi * dx + cosPhi * dy
        // 半径が足りなければ広げる
        let lambda = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
        if lambda > 1 { rx *= sqrt(lambda); ry *= sqrt(lambda) }
        let num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
        let den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
        var coef = den == 0 ? 0 : sqrt(max(num / den, 0))
        if largeArc == sweep { coef = -coef }
        let cxp = coef * rx * y1p / ry
        let cyp = -coef * ry * x1p / rx
        let cx = cosPhi * cxp - sinPhi * cyp + (p0.x + p1.x) / 2
        let cy = sinPhi * cxp + cosPhi * cyp + (p0.y + p1.y) / 2

        func angle(_ ux: Double, _ uy: Double, _ vx: Double, _ vy: Double) -> Double {
            let a = atan2(ux * vy - uy * vx, ux * vx + uy * vy)
            return a
        }
        let theta1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
        var delta = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
        if !sweep && delta > 0 { delta -= 2 * .pi }
        if sweep && delta < 0 { delta += 2 * .pi }

        let segments = max(Int((abs(delta) / (.pi / 2)).rounded(.up)), 1)
        let step = delta / Double(segments)
        let k = 4.0 / 3.0 * tan(step / 4)
        func ellipsePoint(_ t: Double) -> CGPoint {
            let x = rx * cos(t), y = ry * sin(t)
            return CGPoint(x: cx + cosPhi * x - sinPhi * y, y: cy + sinPhi * x + cosPhi * y)
        }
        func derivative(_ t: Double) -> CGPoint {
            let x = -rx * sin(t), y = ry * cos(t)
            return CGPoint(x: cosPhi * x - sinPhi * y, y: sinPhi * x + cosPhi * y)
        }
        var t = theta1
        for i in 0..<segments {
            let t2 = t + step
            let a = ellipsePoint(t), b = i == segments - 1 ? p1 : ellipsePoint(t2)
            let da = derivative(t), db = derivative(t2)
            path.addCurve(to: b, control1: CGPoint(x: a.x + k * da.x, y: a.y + k * da.y),
                          control2: CGPoint(x: b.x - k * db.x, y: b.y - k * db.y))
            t = t2
        }
    }

    /// `d` の文字列を数とコマンドの文字に分ける
    struct Tokenizer {
        private let chars: [Character]
        private var index = 0

        init(_ string: String) { chars = Array(string) }

        var isAtEnd: Bool { index >= chars.count }

        mutating func skipSeparators() {
            while index < chars.count, chars[index].isWhitespace || chars[index] == "," { index += 1 }
        }

        /// 次がコマンドの文字（数の始まりでない英字）なら読む
        mutating func letter() -> Character? {
            skipSeparators()
            guard index < chars.count else { return nil }
            let c = chars[index]
            guard c.isLetter, c != "e", c != "E" else { return nil }
            index += 1
            return c
        }

        /// 数を読む。「10-5」「.5.5」「1e-3」のような詰めた書き方も分ける
        mutating func number() -> Double? {
            skipSeparators()
            var s = ""
            var i = index
            if i < chars.count, chars[i] == "-" || chars[i] == "+" { s.append(chars[i]); i += 1 }
            var seenDot = false, seenDigit = false
            while i < chars.count {
                let c = chars[i]
                if c.isASCII, c.isNumber { s.append(c); seenDigit = true }
                else if c == ".", !seenDot { s.append(c); seenDot = true }
                else { break }
                i += 1
            }
            if seenDigit, i < chars.count, chars[i] == "e" || chars[i] == "E" {
                var e = "e"
                var j = i + 1
                if j < chars.count, chars[j] == "-" || chars[j] == "+" { e.append(chars[j]); j += 1 }
                var expDigits = false
                while j < chars.count, chars[j].isASCII, chars[j].isNumber { e.append(chars[j]); j += 1; expDigits = true }
                if expDigits { s += e; i = j }
            }
            guard seenDigit, let value = Double(s), value.isFinite else { return nil }
            index = i
            return value
        }

        /// 弧のフラグ（0 か 1。「0 1」でも「01」でも読む）
        mutating func flag() -> Bool? {
            skipSeparators()
            guard index < chars.count else { return nil }
            switch chars[index] {
            case "0": index += 1; return false
            case "1": index += 1; return true
            default: return nil
            }
        }
    }
}
