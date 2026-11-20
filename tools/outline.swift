// Turns a line of text into SVG path data, using a font installed on this Mac.
//
// GitHub shows README SVGs as images, and an SVG image cannot load a web font,
// so every piece of type in assets/ is drawn as outlines.
//
//   outline <PostScriptName> <size> <tracking> <text>
//
// Prints one JSON object: { "d": path data, "width": advance width }.
// The path sits on a baseline at y = 0, starts at x = 0, and y grows downward.

import CoreGraphics
import CoreText
import Foundation

let args = CommandLine.arguments
guard args.count == 5, let size = Double(args[2]), let tracking = Double(args[3]) else {
    FileHandle.standardError.write("usage: outline <PostScriptName> <size> <tracking> <text>\n".data(using: .utf8)!)
    exit(2)
}
let fontName = args[1]
let text = args[4]

let font = CTFontCreateWithName(fontName as CFString, CGFloat(size), nil)
let resolved = CTFontCopyPostScriptName(font) as String
guard resolved == fontName else {
    FileHandle.standardError.write("font \(fontName) is not installed (got \(resolved))\n".data(using: .utf8)!)
    exit(1)
}

let attributed = NSAttributedString(
    string: text,
    attributes: [
        NSAttributedString.Key(kCTFontAttributeName as String): font,
        NSAttributedString.Key(kCTKernAttributeName as String): tracking,
    ])
let line = CTLineCreateWithAttributedString(attributed)

func number(_ value: CGFloat) -> String {
    let rounded = (Double(value) * 100).rounded() / 100
    return rounded == rounded.rounded() ? String(Int(rounded)) : String(rounded)
}

var d = ""
for run in CTLineGetGlyphRuns(line) as! [CTRun] {
    let count = CTRunGetGlyphCount(run)
    var glyphs = [CGGlyph](repeating: 0, count: count)
    var positions = [CGPoint](repeating: .zero, count: count)
    CTRunGetGlyphs(run, CFRange(location: 0, length: count), &glyphs)
    CTRunGetPositions(run, CFRange(location: 0, length: count), &positions)
    let attributes = CTRunGetAttributes(run) as NSDictionary
    let runFont = attributes[kCTFontAttributeName as String] as! CTFont

    for index in 0..<count {
        // Flip y: fonts draw upward from the baseline, SVG draws downward.
        var transform = CGAffineTransform(a: 1, b: 0, c: 0, d: -1, tx: positions[index].x, ty: positions[index].y)
        guard let path = CTFontCreatePathForGlyph(runFont, glyphs[index], &transform) else { continue }
        path.applyWithBlock { element in
            let p = element.pointee.points
            switch element.pointee.type {
            case .moveToPoint: d += "M\(number(p[0].x)) \(number(p[0].y))"
            case .addLineToPoint: d += "L\(number(p[0].x)) \(number(p[0].y))"
            case .addQuadCurveToPoint:
                d += "Q\(number(p[0].x)) \(number(p[0].y)) \(number(p[1].x)) \(number(p[1].y))"
            case .addCurveToPoint:
                d += "C\(number(p[0].x)) \(number(p[0].y)) \(number(p[1].x)) \(number(p[1].y)) \(number(p[2].x)) \(number(p[2].y))"
            case .closeSubpath: d += "Z"
            @unknown default: break
            }
        }
    }
}

// The trailing tracking is not part of the visible width.
let width = CTLineGetTypographicBounds(line, nil, nil, nil) - (text.isEmpty ? 0 : tracking)
let output: [String: Any] = ["d": d, "width": (width * 100).rounded() / 100]
print(String(data: try! JSONSerialization.data(withJSONObject: output), encoding: .utf8)!)
