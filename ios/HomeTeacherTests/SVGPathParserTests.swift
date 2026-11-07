import CoreGraphics
import Foundation
import SwiftUI
import Testing
@testable import HomeTeacher

/// 自由に描く黒板の path（#173）
struct SVGPathParserTests {
    private func elements(_ d: String) -> [Path.Element] {
        var out: [Path.Element] = []
        SVGPathParser.path(from: d).forEach { out.append($0) }
        return out
    }

    private func close(_ a: CGPoint, _ b: CGPoint) -> Bool { abs(a.x - b.x) < 0.01 && abs(a.y - b.y) < 0.01 }

    @Test func 絶対座標の直線と閉じる() {
        let e = elements("M10 10 L20 10 H30 V40 Z")
        #expect(e.count == 5)
        #expect(e[0] == .move(to: CGPoint(x: 10, y: 10)))
        #expect(e[2] == .line(to: CGPoint(x: 30, y: 10)))
        #expect(e[3] == .line(to: CGPoint(x: 30, y: 40)))
        #expect(e[4] == .closeSubpath)
    }

    @Test func 相対座標とMのあとの座標の続き() {
        let e = elements("m10 10 5 0 l0 5 h-5 v-5")
        #expect(e.map { if case .line(let p) = $0 { return p } else if case .move(let p) = $0 { return p } else { return .zero } }
            == [CGPoint(x: 10, y: 10), CGPoint(x: 15, y: 10), CGPoint(x: 15, y: 15), CGPoint(x: 10, y: 15), CGPoint(x: 10, y: 10)])
    }

    @Test func 詰めた数の書き方も読む() {
        // 「10-5」は 10 と -5、「.5.5」は 0.5 と 0.5、カンマも区切り
        let e = elements("M10-5L.5.5,1e1 2")
        #expect(e[0] == .move(to: CGPoint(x: 10, y: -5)))
        #expect(e[1] == .line(to: CGPoint(x: 0.5, y: 0.5)))
        #expect(e[2] == .line(to: CGPoint(x: 10, y: 2)))
    }

    @Test func 曲線のSとTは前の制御点を反転する() {
        let e = elements("M0 0 C10 0 20 10 20 20 S30 40 40 40 Q50 30 60 40 T80 40")
        guard case .curve(_, _, let c2) = e[1], case .curve(_, let s1, _) = e[2],
              case .quadCurve(_, let q) = e[3], case .quadCurve(_, let t) = e[4] else {
            Issue.record("曲線になっていない: \(e)")
            return
        }
        #expect(c2 == CGPoint(x: 20, y: 10))
        #expect(s1 == CGPoint(x: 20, y: 30))
        #expect(q == CGPoint(x: 50, y: 30))
        #expect(t == CGPoint(x: 70, y: 50))
    }

    @Test func 弧は終点にたどり着く() {
        let path = SVGPathParser.path(from: "M10 30 A10 10 0 0 1 30 30")
        #expect(close(path.currentPoint ?? .zero, CGPoint(x: 30, y: 30)))
        // 上へふくらむ半円（sweep=1 で y が小さい方を通る）
        let box = path.boundingRect
        #expect(abs(box.minY - 20) < 0.5)
        // 弧のフラグを詰めて書いても読む
        let packed = SVGPathParser.path(from: "M10 30A10 10 0 0130 30")
        #expect(close(packed.boundingRect.origin, box.origin))
    }

    @Test func 壊れた文字列はそこまでを描いて落ちない() {
        #expect(SVGPathParser.path(from: "").isEmpty)
        #expect(SVGPathParser.path(from: "こんにちは").isEmpty)
        #expect(SVGPathParser.path(from: "10 20 30").isEmpty)
        let e = elements("M0 0 L10 10 X 5 5 L20 20")
        #expect(e.count == 2)
        let cut = elements("M0 0 L10 10 C1 2 3")
        #expect(cut.count == 2)
    }

    @Test func 黒板の外の座標は近くに収める() {
        let box = SVGPathParser.path(from: "M-500 0 L500 900").boundingRect
        #expect(box.minX >= -10 && box.maxX <= ChalkDrawing.width + 10)
        #expect(box.maxY <= ChalkDrawing.height + 10)
    }

    @Test func 長すぎるパスは途中で打ち切る() {
        let d = "M0 0 " + Array(repeating: "l1 0", count: 2000).joined(separator: " ")
        #expect(elements(d).count <= SVGPathParser.maxCommands)
    }

    @Test func 部品のpathとして読めて描ける() throws {
        let json = #"{"title":"葉","component":{"type":"chalk_drawing","shapes":[{"kind":"path","d":"M20 40 Q35 20 55 40 Q35 58 20 40 Z","points":[],"text":"葉"}]}}"#
        guard case .component(_, .chalkDrawing(let m)) = BoardTools.content(toolName: BoardTools.showBoardName, input: Data(json.utf8)) else {
            Issue.record("読めない")
            return
        }
        let geometry = ChalkGeometry(shape: try #require(m.shapes.first))
        #expect(!geometry.stroke.isEmpty)
        #expect(geometry.labels.first?.text == "葉")
        // ラベルは形のすぐ下
        #expect((geometry.labels.first?.at.y ?? 0) > geometry.stroke.boundingRect.maxY)
    }

    @Test func dのない古い図も読める() throws {
        let data = Data(#"{"kind":"line","points":[[0,0],[1,1]],"radius":0,"text":"","stamp":"","size":0,"color":"","dashed":false,"fill":false,"step":1}"#.utf8)
        let shape = try JSONDecoder().decode(ChalkDrawing.Shape.self, from: data)
        #expect(shape.d.isEmpty)
    }

    @Test func 答えが数でもパスの形は隠さない() throws {
        let guardian = AnswerLeakGuard(answer: "20", variants: ["20"])
        let json = #"{"title":"形","component":{"type":"chalk_drawing","shapes":[{"kind":"path","d":"M20 20 L40 20","text":"20cm","points":[[30,15]]}]}}"#
        let masked = guardian.mask(BoardTools.content(toolName: BoardTools.showBoardName, input: Data(json.utf8)))
        guard case .component(_, .chalkDrawing(let m)) = masked.content else {
            Issue.record("読めない")
            return
        }
        #expect(m.shapes[0].d == "M20 20 L40 20")
        #expect(m.shapes[0].text == AnswerLeakGuard.maskText)
    }
}
