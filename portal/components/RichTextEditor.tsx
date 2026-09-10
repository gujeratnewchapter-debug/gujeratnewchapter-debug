'use client';

import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import TextStyle from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import TextAlign from '@tiptap/extension-text-align';
import {
  Bold, Italic, AlignLeft, AlignCenter, AlignRight, List, ListOrdered,
  Heading1, Heading2, Heading3, Minus, Quote, LayoutTemplate,
} from 'lucide-react';

interface Props {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
}

const SWATCHES = ['#FFFFFF', '#123B5D', '#10B981', '#34D399', '#0F766E', '#F59E0B'];

const STUDY_GUIDE_TEMPLATE = `
<h2>Why This Exists</h2>
<p>Introduce the topic and explain why it matters.</p>
<hr>
<h2>Article 1 - Short Title</h2>
<p><strong>Key term:</strong> Define the important concept in clear language.</p>
<h3>Key Points</h3>
<ul><li>Summarize the first important rule.</li><li>Summarize the second important rule.</li></ul>
<blockquote><p><strong>Exam Takeaway</strong><br>State the rule or idea learners should remember.</p></blockquote>
`;

export function RichTextEditor({ value, onChange, placeholder }: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      TextStyle,
      Color,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
    ],
    content: value || '',
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
    editorProps: {
      attributes: { class: 'rich-editor-content' },
    },
    immediatelyRender: false,
  });

  if (!editor) return null;

  return (
    <div>
      <div className="rich-toolbar">
        <button type="button" onClick={() => editor.chain().focus().toggleBold().run()} className={editor.isActive('bold') ? 'active' : ''} title="Bold">
          <Bold size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().toggleItalic().run()} className={editor.isActive('italic') ? 'active' : ''} title="Italic">
          <Italic size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} className={editor.isActive('heading', { level: 1 }) ? 'active' : ''} title="Title heading">
          <Heading1 size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} className={editor.isActive('heading', { level: 2 }) ? 'active' : ''} title="Section heading">
          <Heading2 size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} className={editor.isActive('heading', { level: 3 }) ? 'active' : ''} title="Subheading">
          <Heading3 size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().toggleBulletList().run()} className={editor.isActive('bulletList') ? 'active' : ''} title="Bullet list">
          <List size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().toggleOrderedList().run()} className={editor.isActive('orderedList') ? 'active' : ''} title="Numbered list">
          <ListOrdered size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().setTextAlign('left').run()} className={editor.isActive({ textAlign: 'left' }) ? 'active' : ''} title="Align left">
          <AlignLeft size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().setTextAlign('center').run()} className={editor.isActive({ textAlign: 'center' }) ? 'active' : ''} title="Align center">
          <AlignCenter size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().setTextAlign('right').run()} className={editor.isActive({ textAlign: 'right' }) ? 'active' : ''} title="Align right">
          <AlignRight size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().setHorizontalRule().run()} title="Insert section divider">
          <Minus size={15} />
        </button>
        <button type="button" onClick={() => editor.chain().focus().toggleBlockquote().run()} className={editor.isActive('blockquote') ? 'active' : ''} title="Exam takeaway callout">
          <Quote size={15} />
        </button>
        {editor.isEmpty && (
          <button type="button" onClick={() => editor.commands.setContent(STUDY_GUIDE_TEMPLATE)} title="Insert study guide template">
            <LayoutTemplate size={15} />
          </button>
        )}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', paddingLeft: 6, marginLeft: 4, borderLeft: '1px solid var(--border)' }}>
          {SWATCHES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => editor.chain().focus().setColor(c).run()}
              title={c}
              style={{ width: 16, height: 16, borderRadius: '50%', background: c, border: '1px solid var(--border)', padding: 0 }}
            />
          ))}
        </div>
      </div>
      <div className="rich-editor">
        <EditorContent editor={editor} />
        {editor.isEmpty && placeholder && (
          <p style={{ color: 'var(--text-muted)', position: 'relative', top: -24, pointerEvents: 'none', margin: 0 }}>{placeholder}</p>
        )}
      </div>
    </div>
  );
}
