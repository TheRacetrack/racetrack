package main

import (
	"bytes"
	"fmt"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	log "github.com/inconshreveable/log15"
	"github.com/mattn/go-colorable"
	"github.com/pkg/errors"
)

const (
	timeFormat  = "2006-01-02T15:04:05-0700"
	termMsgJust = 40
	errorKey    = "LOG15_ERROR"
	floatFormat = 'f'
)

func ConfigureLog(logLevel string, structuredLogging bool) {
	lvl, err := log.LvlFromString(logLevel)
	if err != nil {
		panic(errors.Wrap(err, "parsing log level"))
	}

	var format log.Format
	if structuredLogging {
		format = log.JsonFormat()
	} else {
		format = sortedLogfmtFormat()
	}

	handler := log.StreamHandler(colorable.NewColorableStdout(), format)
	handler = log.LvlFilterHandler(lvl, handler)
	log.Root().SetHandler(handler)
}

func sortedLogfmtFormat() log.Format {
	return log.FormatFunc(func(r *log.Record) []byte {
		log15format := TerminalFormat()
		r.Ctx = sortContext(r.Ctx)
		return log15format.Format(r)
	})
}

// sortContext sorts context variables by keys in alphabetical order,
// thus making logs easier to read and compare
func sortContext(ctx []interface{}) []interface{} {
	ctxMap := make(map[string]interface{})
	for i := 0; i < len(ctx); i += 2 {
		k := ctx[i].(string)
		val := ctx[i+1]
		ctxMap[k] = val
	}

	keys := make([]string, 0)
	for k := range ctxMap {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	sortedCtx := make([]interface{}, len(keys)*2)
	for i, k := range keys {
		sortedCtx[i*2] = k
		sortedCtx[i*2+1] = ctxMap[k]
	}
	return sortedCtx
}

func LogfmtFormat() log.Format {
	return log.FormatFunc(func(r *log.Record) []byte {
		common := []interface{}{r.KeyNames.Time, r.Time, r.KeyNames.Lvl, r.Lvl, r.KeyNames.Msg, r.Msg}
		buf := &bytes.Buffer{}
		logfmt(buf, append(common, r.Ctx...), 0)
		return buf.Bytes()
	})
}

func TerminalFormat() log.Format {
	return log.FormatFunc(func(r *log.Record) []byte {
		var color = 0
		switch r.Lvl {
		case log.LvlCrit:
			color = 35
		case log.LvlError:
			color = 31
		case log.LvlWarn:
			color = 33
		case log.LvlInfo:
			color = 32
		case log.LvlDebug:
			color = 36
		}

		b := &bytes.Buffer{}
		lvl := strings.ToUpper(r.Lvl.String())
		if color > 0 {
			fmt.Fprintf(b, "[%s] \x1b[%dm%s\x1b[0m %s ", r.Time.Format(timeFormat), color, lvl, r.Msg)
		} else {
			fmt.Fprintf(b, "[%s] %s %s ", r.Time.Format(timeFormat), lvl, r.Msg)
		}

		// try to justify the log output for short messages
		if len(r.Ctx) > 0 && len(r.Msg) < termMsgJust {
			b.Write(bytes.Repeat([]byte{' '}, termMsgJust-len(r.Msg)))
		}

		// print the keys logfmt style
		logfmt(b, r.Ctx, color)
		return b.Bytes()
	})
}

func logfmt(buf *bytes.Buffer, ctx []interface{}, color int) {
	for i := 0; i < len(ctx); i += 2 {
		if i != 0 {
			buf.WriteByte(' ')
		}

		k, ok := ctx[i].(string)
		v := formatLogfmtValue(ctx[i+1])
		if !ok {
			k, v = errorKey, formatLogfmtValue(k)
		}

		if color > 0 {
			fmt.Fprintf(buf, "\x1b[%dm%s\x1b[0m=%s", color, k, v)
		} else {
			buf.WriteString(k)
			buf.WriteByte('=')
			buf.WriteString(v)
		}
	}

	buf.WriteByte('\n')
}

func formatLogfmtValue(value interface{}) string {
	if value == nil {
		return "nil"
	}

	if t, ok := value.(time.Time); ok {
		return t.Format(timeFormat)
	}
	value = formatShared(value)
	switch v := value.(type) {
	case bool:
		return strconv.FormatBool(v)
	case float32:
		return strconv.FormatFloat(float64(v), floatFormat, 3, 64)
	case float64:
		return strconv.FormatFloat(v, floatFormat, 3, 64)
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64:
		return fmt.Sprintf("%d", value)
	case string:
		return escapeString(v)
	default:
		return escapeString(fmt.Sprintf("%+v", value))
	}
}

func formatShared(value interface{}) (result interface{}) {
	defer func() {
		if err := recover(); err != nil {
			if v := reflect.ValueOf(value); v.Kind() == reflect.Ptr && v.IsNil() {
				result = "nil"
			} else {
				panic(err)
			}
		}
	}()

	switch v := value.(type) {
	case time.Time:
		return v.Format(timeFormat)

	case error:
		return v.Error()

	case fmt.Stringer:
		return v.String()

	default:
		return v
	}
}

var stringBufPool = sync.Pool{
	New: func() interface{} { return new(bytes.Buffer) },
}

func escapeString(s string) string {
	needsQuotes := false
	needsEscape := false
	for _, r := range s {
		if r <= ' ' || r == '=' || r == '"' {
			needsQuotes = true
		}
		if r == '\\' || r == '"' || r == '\n' || r == '\r' || r == '\t' {
			needsEscape = true
		}
	}
	if !needsEscape && !needsQuotes {
		return s
	}
	e := stringBufPool.Get().(*bytes.Buffer)
	e.WriteByte('"')
	for _, r := range s {
		switch r {
		case '\\', '"':
			e.WriteByte('\\')
			e.WriteByte(byte(r))
		case '\n':
			e.WriteString("\\n")
		case '\r':
			e.WriteString("\\r")
		case '\t':
			e.WriteString("\\t")
		default:
			e.WriteRune(r)
		}
	}
	e.WriteByte('"')
	var ret string
	if needsQuotes {
		ret = e.String()
	} else {
		ret = string(e.Bytes()[1 : e.Len()-1])
	}
	e.Reset()
	stringBufPool.Put(e)
	return ret
}
